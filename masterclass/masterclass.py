# -*- coding: utf-8 -*-
"""
An XBlock that facilitates offline teacher-student gatherings.
"""

import pkg_resources

from xblock.core import XBlock
from xblock.fields import Scope, Integer, String, Boolean, List
from xblock.fragment import Fragment

from django.template import Context as DjangoContext
from django.template import Template as DjangoTemplate
from django.utils.encoding import iri_to_uri

# Yeah, yeah.
from django.contrib.auth.models import User

# And here we reach even deeper into the guts of edX
try:
    from bulk_email.models import CourseEmailTemplate
    from bulk_email.tasks import _get_course_email_context as get_email_context
    from bulk_email.tasks import _get_source_address as get_source_address
    from courseware import courses as CourseData
except:
    # Except we're running in Studio, so all of this stuff isn't available.
    # It's interesting that modules actually do import, they just don't finish loading,
    # because Studio doesn't provide the requisite settings.*
    # Thankfully we aren't going to need it while running in Studio.
    pass

from django.core import mail

import codecs, io
import unicodecsv

from webob.response import Response

import logging

log = logging.getLogger(__name__)


@XBlock.needs("user")
class MasterclassXBlock(XBlock):
    """
    An XBlock that contains functionality for
    holding "master-classes", offline gatherings
    between teachers and students, with accompanying invitations,
    participant counts, etc.
    """

    @staticmethod
    def render_template_from_string(template_string, **kwargs):
        """Loads the django template for `template_name`"""
        template = DjangoTemplate(template_string)
        return template.render(DjangoContext(kwargs))

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    # Settings fields.

    # Um. So how do I i18n those when I can't self._ ?

    display_name = String(
        display_name=u"Имя модуля",
        help=u"Это имя будет использовано в заголовке и в строках навигации",
        scope=Scope.settings,
        default=u"Регистрация на мастер-класс"
    )

    capacity = Integer(
        display_name=u"Количество свободных мест",
        help=u"Максимальное количество свободных мест в месте проведения мастер-класса",
        default=30,
        scope=Scope.settings,
        values={"min": 1},
    )

    approval_required = Boolean(
        display_name=u"Регистрация требует подтверждения преподавателем",
        help=u"1/True - регистрация должна быть подтверждена преподавателем, 0/False - нет",
        scope=Scope.settings,
        default=False
    )

    # Student aggregate data.

    approved_registrations = List(
        help=u"Список зарегистрированных студентов.",
        scope=Scope.user_state_summary
    )

    pending_registrations = List(
        help=u"Список заявившихся студентов.",
        scope=Scope.user_state_summary
    )

    def registration_status_string(self, student_id):
        if student_id in self.approved_registrations:
            return u"Вы зарегистрированы на этот мастер-класс."
        elif student_id in self.pending_registrations:
            return u"Ваша заявка ожидает подтверждения преподавателем."
        elif len(self.approved_registrations) >= self.capacity:
            return u"На мастер-классе закончились свободные места."
        return u"Вы можете зарегистрироваться на этот мастер-класс."

    def registration_button_text(self, student_id):
        if student_id in self.approved_registrations or student_id in self.pending_registrations:
            return u"Отказаться"
        return u"Зарегистрироваться"

    def acquire_student_id(self):
        """
        Get the user ID through the user service. Then use the user ID directly for the moment because I don't
        have the time for the rest"""
        user_service = self.runtime.service(self, "user")
        xblock_user = user_service.get_current_user()
        if xblock_user is not None:
            return xblock_user.opt_attrs.get('edx-platform.user_id', None)
        return None


    def acquire_student_name(self, student_id):
        user = User.objects.get(id=student_id)
        return user.profile.name

    def acquire_student_email(self, student_id):
        user = User.objects.get(id=student_id)
        return user.email

    def acquire_student_username(self, student_id):
        user = User.objects.get(id=student_id)
        return user.username

    def acquire_course_name(self):
        return CourseData.get_course(self.course_id).display_name_with_default

    def acquire_parent_name(self):
        return self.xmodule_runtime.get_module(self.get_parent()).display_name_with_default

    def is_user_course_staff(self):
        return self.xmodule_runtime.get_user_role() in ['staff', 'instructor']

    def get_parent(self):
        return self.xmodule_runtime.get_block(self.runtime.modulestore.get_parent_location(self.location))

    def send_email_to_student(self, receivers, subject, text):
        # Instead of sending the email through the rest of the edX bulk mail system,
        # we're going to use the edX email templater, and then toss the email directly through
        # the Django mailer.

        # We're assuming receivers is a list of User IDs.

        emails = []

        email_template = CourseEmailTemplate.get_template()
        context = get_email_context(CourseData.get_course(self.course_id))
        from_address = get_source_address(self.course_id, self.acquire_course_name())

        for student_id in list(set(receivers)):
            context['email'] = self.acquire_student_email(student_id)
            context['name'] = self.acquire_student_name(student_id)

            plaintext_message = email_template.render_plaintext(text, context)
            html_message = email_template.render_htmltext(text, context)

            email_message = mail.EmailMultiAlternatives(subject, plaintext_message, from_address, [context['email']])
            email_message.attach_alternative(html_message, 'text/html')

            emails.append(email_message)

        connection = mail.get_connection()
        connection.send_messages(emails)

        return

    def student_view(self, context=None):
        """
        The primary view of the MasterclassXBlock, shown to students
        when viewing courses.
        """

        student = self.acquire_student_id()

        html = self.resource_string("static/html/masterclass.html")

        frag = Fragment()
        frag.add_css(self.resource_string("static/css/masterclass.css"))
        frag.add_javascript(self.resource_string("static/js/src/masterclass.js"))

        registrants_list = None

        if self.is_user_course_staff():
            registrants_list = []
            if self.approval_required:
                button_text = u"Удалить"
            else:
                button_text = u"Удалить"
            for that_student in self.approved_registrations:
                registrants_list.append(
                    (that_student, self.acquire_student_name(that_student), self.acquire_student_email(that_student),
                     button_text))
            if self.approval_required:
                for that_student in self.pending_registrations:
                    registrants_list.append(
                        (that_student, self.acquire_student_name(that_student),
                         self.acquire_student_email(that_student),
                         u"Одобрить"))
            registrants_list.sort(key=lambda student: student[1])

        frag.add_content(self.render_template_from_string(html,
                                                          display_name=self.display_name,
                                                          capacity=self.capacity,
                                                          is_course_staff=self.is_user_course_staff(),
                                                          free=self.capacity - len(self.approved_registrations),
                                                          button_text=self.registration_button_text(student),
                                                          registrants_list=registrants_list,
                                                          status_string=self.registration_status_string(student),
                                                          ))

        frag.initialize_js('MasterclassXBlock')
        return frag

    # Note that when editing the course in studio, it renders author_view and falls back to student_view.
    # studio_view is the edit-data page.

    def studio_view(self, context=None):
        """
        This is the Studio settings page.
        The neat way of autogenerating it is from Staff Graded Assignment block.
        (Why isn't this the default anyway?)
        """
        cls = type(self)

        def none_to_empty(x):
            return x if x is not None else ''

        edit_fields = (
            (field, none_to_empty(getattr(self, field.name)), validator)
            for field, validator in (
                (cls.display_name, 'string'),
                (cls.capacity, 'number'),
                (cls.approval_required, 'boolean')
            ))

        html = self.resource_string('static/html/masterclass_studio.html')
        fragment = Fragment()
        fragment.add_content(self.render_template_from_string(html, fields=edit_fields))
        fragment.add_javascript(self.resource_string("static/js/src/masterclass_studio.js"))
        fragment.add_css(self.resource_string("static/css/masterclass.css"))
        fragment.initialize_js('MasterclassXBlockStudio')
        return fragment

    def author_view(self, context=None):
        """
        This view shows up in studio.
        Since at this moment, runtime does not seem to allow us to know who the active user is while in studio,
        we'll be using an alternative passive template.
        It's not like there's a point in seeing the register button there anyway.
        """

        html = self.resource_string('static/html/masterclass_author.html')
        fragment = Fragment()
        fragment.add_css(self.resource_string("static/css/masterclass.css"))
        fragment.add_content(self.render_template_from_string(html,
                                                              approval_required=self.approval_required,
                                                              display_name=self.display_name,
                                                              capacity=self.capacity,
                                                              free=self.capacity - len(self.approved_registrations)))
        return fragment

    @XBlock.json_handler
    def approval_button(self, data, suffix=''):
        """
        Handle the approve/unapprove/remove button in registrants list view.
        """

        student = data['student_id']

        if student in self.approved_registrations:
            if self.approval_required:
                self.approved_registrations.remove(student)
                self.pending_registrations.append(student)
                new_button_text = u"Удалить"
            else:
                self.approved_registrations.remove(student)
                new_button_text = u"Зарегистрировать"
        elif student in self.pending_registrations:
            if self.approval_required:
                self.pending_registrations.remove(student)
                self.approved_registrations.append(student)
                # For the moment that will suffice, I need to test the whole email mechanism first...
                self.send_email_to_student([student], u"О вашей регистрации на мастер-класс.",
                                           u"Ваша заявка на мастер-класс {course_name} - {parent_name} была одобрена.".format(
                                               course_name=self.acquire_course_name(),
                                               parent_name=self.acquire_parent_name()))
                new_button_text = u"Снять регистрацию"
            else:
                # This branch shouldn't happen.
                # If approval isn't required, the list should be empty,
                # and the button shouldn't exist.
                raise
        else:
            if self.approval_required:
                self.pending_registrations.append(student)
                new_button_text = u"Одобрить"
            else:
                self.approved_registrations.append(student)
                new_button_text = u"Удалить"

        return {'button_text': new_button_text,
                'student_id': student}

    @XBlock.handler
    def get_csv(self, data, suffix=''):
        """This function should send a CSV of all the approved registrants to the user."""

        if not self.is_user_course_staff():
            log.error("Somehow someone other than course staff has requested a CSV of master-class registrants")
            return

        results = []

        parent_name = self.acquire_parent_name()
        course_name = self.acquire_course_name()

        filename = u"{0} - {1}.csv".format(course_name, parent_name)

        for student in self.approved_registrations:
            results.append(
                {
                    "username": self.acquire_student_username(student),
                    "email": self.acquire_student_email(student),
                    "name": self.acquire_student_name(student),
                }
            )

        if len(results):
            with io.BytesIO() as handle:
                writer = unicodecsv.DictWriter(handle, results[0].keys(), encoding='utf-8',
                                               dialect=unicodecsv.excel)
                writer.writeheader()
                for row in results:
                    writer.writerow(row)
                # Notice the enforced UTF-8 byte order mark here.
                # This ensures that Windows Excel can read an UTF-8 encoded CSV correctly
                # It does not appear to hinder any other programs that can read CSV.
                output_string = codecs.BOM_UTF8 + handle.getvalue()

            return Response(
                charset='utf8',
                body=output_string,
                content_type="text/csv",
                content_disposition="attachment; filename*=UTF-8''{0}".format(iri_to_uri(filename))
            )

    @XBlock.json_handler
    def send_mail_to_all(self, data, suffix=''):
        if not self.is_user_course_staff():
            log.error("Somehow someone other than course staff tried to send mail to all master-class registrants.")
            return

        subject = data.get('subject')
        text = data.get('text')
        if subject and text:
            self.send_email_to_student(self.approved_registrations + [self.acquire_student_id()], subject, text)
            return {'status': "ok"}
        else:
            return {'status': "fail"}


    @XBlock.json_handler
    def register_button(self, data, suffix=''):
        """
        Handle the register button in LMS. Notice this button both registers and unregisters.
        """

        student = self.acquire_student_id()

        if student is None:
            return {'registration_status': u"Кнопка регистрации не работает в Студии и не должна.",
                    "button_text": u"Зарегистрироваться"}

        if student in self.pending_registrations:
            self.pending_registrations.remove(student)
            result_message = u"Вы сняли заявку на участие в этом мастер-классе."
        elif student in self.approved_registrations:
            self.approved_registrations.remove(student)
            result_message = u"Вы сняли регистрацию на участие в этом мастер-классе."
        else:
            if (self.capacity - len(self.approved_registrations)) > 0:
                if self.approval_required:
                    self.pending_registrations.append(student)
                    result_message = u"Ваша заявка на участие ожидает одобрения преподавателем."
                else:
                    self.approved_registrations.append(student)
                    result_message = u"Вы были успешно зарегистрированы."
            else:
                result_message = u"Свободных мест больше нет, извините."

        return {'registration_status': result_message,
                "button_text": self.registration_button_text(student)}

    @XBlock.json_handler
    def save_masterclass(self, data, suffix=''):
        """Save settings in Studio"""
        for name in ['display_name', 'capacity']:
            setattr(self, name, data.get(name, getattr(self, name)))
        if data.get('approval_required').lower() in ["true", "yes", "1"]:
            self.approval_required = True
        else:
            self.approval_required = False

