"""
An XBlock that facilitates offline teacher-student gatherings.
"""

import pkg_resources

from xblock.core import XBlock
from xblock.fields import Scope, Integer, String, Boolean, List
from xblock.fragment import Fragment

from django.template import Context as DjangoContext
from django.template import Template as DjangoTemplate

# Yeah, yeah.
from django.contrib.auth.models import User

from xmodule.exceptions import UndefinedContext

import logging

log = logging.getLogger('masterclass')

import pdb


class MasterclassXBlock(XBlock):
    """
    An XBlock that contains functionality for
    holding "master-classes", offline gatherings
    between teachers and students, with accompanying invitations,
    participant counts, etc.
    """

    icon_class = 'other'

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

    display_name = String(
        display_name="Display Name",
        help="This name appears in the horizontal navigation at the top of the page.",
        scope=Scope.settings,
        default="Master-class registration"
    )

    capacity = Integer(
        display_name="Venue capacity",
        help="Maximum capacity of the venue the masterclass will be held in, a number of students.",
        default=30,
        scope=Scope.settings,
        values={"min": 1},
    )

    minimum_score = Integer(
        display_name="Required test score",
        help="If the master-class block has an attached problem, this is the score required for registering.",
        scope=Scope.settings,
        default=250,
        values={"min": 1},
    )

    approval_required = Boolean(
        display_name="Manual approval",
        help="Whether student registration requires manual approval.",
        scope=Scope.settings,
        default=False
    )

    # Student aggregate data.

    approved_registrations = List(
        help="List of approved student registrations.",
        scope=Scope.user_state_summary
    )

    pending_registrations = List(
        help="List of pending student registrations.",
        scope=Scope.user_state_summary
    )

    # A view for the studio seems to be called 'studio_view'.
    # LMS view for the instructor is 'instructor_view'? Maybe.
    # Another interesting name is 'fallback_view'
    # Blocks having children are supposed to call their renderers 
    # with render_children...

    def registration_status_string(self, student_id):
        if student_id in self.approved_registrations:
            return "You are registered for this master-class."
        elif student_id in self.pending_registrations:
            return "Your registration is waiting for staff approval."
        elif len(self.approved_registrations) >= self.capacity:
            return "There are no free spaces remaining to register for this master-class."
        elif self.is_registration_allowed():
            return "You can register for this master-class.".format(
                capacity=self.capacity - len(self.approved_registrations))
        return "You need to complete the test to register for this master-class."

    def registration_button_text(self, student_id):
        if student_id in self.approved_registrations or student_id in self.pending_registrations:
            return "Unregister"
        return "Register"

    def acquire_student_id(self):
        """
        This is a wrapper function to abstract away the api-breaking fact that I can't know who the user is.
        """
        try:
            return self.xmodule_runtime.get_real_user(self.xmodule_runtime.anonymous_student_id).id
        except TypeError:
            return None


    def acquire_student_name(self, student_id):
        user = User.objects.get(id=student_id)
        return user.get_full_name()

    def acquire_student_username(self, student_id):
        user = User.objects.get(id=student_id)
        return user.username

    def acquire_student_email(self, student_id):
        user = User.objects.get(id=student_id)
        return user.email

    def show_control_panel(self):
        return self.xmodule_runtime.get_user_role() in ['staff', 'instructor']

    def get_peer_blocks(self):
        # Technically, I should be able to only do this in studio view,
        # and save the location of the actual test or tests... but that can wait,
        # and also has potential problems like "so how do we force it to recalculate".

        try:
            # For some curious reason, get_parent() currently returns none.
            # Could it be it does not refer to XModule parents?
            peers = [self.runtime.get_block(child_name) for child_name in self.get_parent().children]
        except AttributeError:
            # So we dig through the location tree instead.
            parent_location = self.runtime.modulestore.get_parent_location(self.location)
            peers = self.runtime.get_block(parent_location).get_children()

        return peers

    def is_registration_allowed_by_test(self):
        """
        Determine if a test is required to join this masterclass.
        We're assuming that this is the fact when the masterclass has any peers,
        i.e. modules with the same location parent as itself, which
        return a score. For the moment only the first block found that does is counted as relevant.

        """

        peers = self.get_peer_blocks()

        # Now that we have a list of peers, walk it and see if any of them are problems.
        for peer in peers:
            if peer is self:
                continue
            if peer.has_score:
                # Now, this will work only if the runtime is defined,
                # and when the user has a score on this module...
                try:
                    # I'm pretty this is outside the bounds of the API.
                    # By this point I'm not sure what IS the API though.

                    # It is supremely bizarre, but the first time you get_score(), you always get a zero.
                    scoredata = self.xmodule_runtime.get_module(peer).get_score()

                    # The second time returns correct data, however.
                    # There's got to be a race condition somewhere, but I'm not up to finding it right now.
                    problem_score = self.xmodule_runtime.get_module(peer).get_score()['score']


                    # If the problem score condition is satisfied, registration is allowed by test.
                    log.warning("Problem score: {0}, required score: {1}".format(problem_score, self.minimum_score))
                    return problem_score >= self.minimum_score
                except AttributeError:
                    # We get an AttributeError if the score is None.
                    log.warning("Somehow, score returned was none.")
                except UndefinedContext:
                    # We get an UndefinedContext when in Studio, where, apparently,
                    # it does not yet exist during initial page rendering.
                    log.error("Context was undefined. It should not happen, so if it did, there's a problem.")
                # If we can't get the score, but we know a problem exists, registration is not allowed.

                return False

        # If we didn't find any peers with a score, registration is allowed by test.
        return True

    def is_registration_allowed(self):
        if (self.capacity - len(self.approved_registrations)) <= 0:
            # There's no reason to check anything else if we're over capacity.
            return False
        # Otherwise, it is determined by the existence of a test.
        return self.is_registration_allowed_by_test()


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

        if student is not None and self.show_control_panel():
            registrants_list = []
            if self.approval_required:
                button_text = "Unapprove"
            else:
                button_text = "Remove"
            for that_student in self.approved_registrations:
                registrants_list.append(
                    (that_student, self.acquire_student_name(that_student), self.acquire_student_email(that_student),
                     button_text))
            if self.approval_required:
                for that_student in self.pending_registrations:
                    registrants_list.append(
                        (that_student, self.acquire_student_name(that_student), self.acquire_student_email(that_student),
                        "Approve"))

        frag.add_content(self.render_template_from_string(html,
                                                          display_name=self.display_name,
                                                          capacity=self.capacity,
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
            (cls.minimum_score, 'number'),
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

        test_required = None
        for peer in self.get_peer_blocks():
            if peer.has_score:
                test_required = peer.location
                break

        html = self.resource_string('static/html/masterclass_author.html')
        fragment = Fragment()
        fragment.add_css(self.resource_string("static/css/masterclass.css"))
        fragment.add_content(self.render_template_from_string(html,
                                                              test_required=test_required,
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
                new_button_text = "Remove"
            else:
                self.approved_registrations.remove(student)
                new_button_text = "Register"
        elif student in self.pending_registrations:
            if self.approval_required:
                self.pending_registrations.remove(student)
                self.approved_registrations.append(student)
                new_button_text = "Unapprove"
            else:
                # This branch shouldn't happen.
                # If approval isn't required, the list should be empty,
                # and the button shouldn't exist.
                self.pending_registrations.remove(student)
                new_button_text = "Something odd happened"
        else:
            if self.approval_required:
                self.pending_registrations.append(student)
                new_button_text = "Approve"
            else:
                self.approved_registrations.append(student)
                new_button_text = "Remove"

        return {'button_text': new_button_text }

    @XBlock.json_handler
    def get_csv(self, data, suffix=''):
        """This function should send a CSV of all the approved registrants to the user."""
        
        return {'button_text':"Ok"}

    @XBlock.json_handler
    def register_button(self, data, suffix=''):
        """
        Handle the register button in LMS. Notice this button both registers and unregisters.
        """

        student = self.acquire_student_id()

        if student is None:
            return {'registration_status': "Registration button does not work in Studio.",
                    "button_text": "Register"}

        if student in self.pending_registrations:
            self.pending_registrations.remove(student)
            result_message = "You are no longer requesting to be registered for this master-class."
        elif student in self.approved_registrations:
            self.approved_registrations.remove(student)
            result_message = "You are no longer registered for this master-class."
        else:
            if (self.capacity - len(self.approved_registrations)) > 0:
                if self.is_registration_allowed_by_test():
                    if self.approval_required:
                        self.pending_registrations.append(student)
                        result_message = "Your request for registration is now waiting for staff approval."
                    else:
                        self.approved_registrations.append(student)
                        result_message = "You have been successfully registered."

                else:
                    result_message = "You have to score highly enough on the test to register."
            else:
                result_message = "There are no free spots remaining, sorry."

        return {'registration_status': result_message,
                "button_text": self.registration_button_text(student)}

    @XBlock.json_handler
    def save_masterclass(self, data, suffix=''):
        """Save settings in Studio"""
        for name in ('display_name', 'capacity', 'minimum_score'):
            setattr(self, name, data.get(name, getattr(self, name)))
        if data.get('approval_required').lower() in ["true", "yes", "1"]:
            self.approval_required = True
        else:
            self.approval_required = False

