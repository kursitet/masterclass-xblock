/* Javascript for MasterclassXBlock. */
function MasterclassXBlock(runtime, element) {

    function updateStatus(result) {
        $('.registration_status', element).text(result.registration_status);
        $('.register_button', element).text(result.button_text);
    }

    $(element).find('.register_button').bind('click', function () {
        var handlerUrl = runtime.handlerUrl(element, 'register_button');
        $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify({"button_clicked": "True"}),
            success: updateStatus
        });
    });

    function updateStudents(result) {

    }

    $(element).find('.student_approval_button').bind('click', function() {
        var handlerUrl = runtime.handlerUrl(element,'approval_button');
        $.ajax({
           type: "POST",
            url: handlerUrl,
            data: JSON.stringify({"student_id":"Meh!"}),
            success: updateStudents
        });
    });
}