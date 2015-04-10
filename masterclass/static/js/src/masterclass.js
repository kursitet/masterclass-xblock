/* Javascript for MasterclassXBlock. */
function MasterclassXBlock(runtime, element) {

    $('.masterclass-get-csv-link', element).attr('href', runtime.handlerUrl(element, 'get_csv'));

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

    $('.register_button', element).click(function (eventObject) {
        // Put a spinner on it so that there's a visual indication it's busy.
        $('.register_button', element).append(' <i class="register-spin fa fa-refresh fa-spin"></i>');
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

    $('.student_approval_button', element).click(function (eventObject) {
        var handlerUrl = runtime.handlerUrl(element, 'approval_button');
        var student_id = $(this).data('student');
        $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify({"student_id": student_id}),
            success: updateStudents
        });
    });

    $('.send-mail-button', element).click(function (eventObject) {
        $('.send-mail-wrapper', element).slideToggle();
    });

    function mailSent(result) {
        $('.send-mail-wrapper', element).slideToggle();
        $('.send-mail-spin', element).remove();
        $('input#email_subject', element).val('');
        $('textarea#email_content',element).val('');
    }

    $('.send-mail-submit', element).click(function (eventObject) {
        $('.send-mail-submit', element).append(' <i class="send-mail-spin fa fa-refresh fa-spin"></i>');
        var handlerUrl = runtime.handlerUrl(element, 'send_mail_to_all');
        $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify({
                "subject": $('input#email_subject', element).val(),
                "text": $('textarea#email_content', element).val()
            }),
            success: mailSent
        });
    });

};

