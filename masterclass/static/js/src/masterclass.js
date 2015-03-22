/* Javascript for MasterclassXBlock. */
function MasterclassXBlock(runtime, element) {

    $(element).find('.masterclass-get-csv-link').attr('href', runtime.handlerUrl(element, 'get_csv'));

    $.ajax({
        type: "POST",
        url: runtime.handlerUrl(element, 'refresh_display'),
        data: JSON.stringify({"display_refreshed": "True"}),
        success: updateStatus
    });

    function updateStatus(result) {
        $('.registration_status', element).text(result.registration_status);
        $('.register_button', element).text(result.button_text);
        $('.capacity', element).text(result.free_places + " / " + result.capacity);
    }

    $(element).find('.register_button').bind('click', function () {
        // Put a spinner on it so that there's a visual indication it's busy.
        $(element).find('.register_button').append(' <i class="register-spin fa fa-refresh fa-spin"></i>');
        var handlerUrl = runtime.handlerUrl(element, 'register_button');
        $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify({"button_clicked": "True"}),
            success: updateStatus
        });
    });

    function updateStudents(result) {
        window.location.reload();

        /*if (result.free_places > 0) {
            $(element).find('.student_approval_button[data-student="' + result.student_id + '"]').remove();
        } else {
            $(element).find('.student_approval_button').remove();
        }
        $(element).find('.capacity').text(result.free_places + " / " + result.capacity);*/
    }

    $(element).find('.student_approval_button').bind('click', function () {
        var handlerUrl = runtime.handlerUrl(element, 'approval_button');
        var student_id = $(this).data('student');
        $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify({"student_id": student_id}),
            success: updateStudents
        });
    });

    $(element).find('.send-mail-button').bind('click', function () {
        $(element).find('.send-mail-wrapper').slideToggle();
    });

    function mailSent(result) {
        $(element).find('.send-mail-wrapper').slideToggle();
        $(element).find('.send-mail-spin').remove();
        $(element).find('input#email_subject').val('');
        $(element).find('textarea#email_content').val('');
    }

    $(element).find('.send-mail-submit').bind('click', function () {
        $(element).find('.send-mail-submit').append(' <i class="send-mail-spin fa fa-refresh fa-spin"></i>');
        var handlerUrl = runtime.handlerUrl(element, 'send_mail_to_all');
        $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify({
                "subject": $(element).find('input#email_subject').val(),
                "text": $(element).find('textarea#email_content').val()
            }),
            success: mailSent
        });
    });

}

