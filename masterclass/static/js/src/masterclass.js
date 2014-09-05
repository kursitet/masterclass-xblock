/* Javascript for MasterclassXBlock. */
function MasterclassXBlock(runtime, element) {

    $(element).find('.masterclass-get-csv-link').attr('href',runtime.handlerUrl(element, 'get_csv'));

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
        $('.student_approval_button', element).text(result.button_text);
    }

    $(element).find('.student_approval_button').bind('click', function () {
        var handlerUrl = runtime.handlerUrl(element, 'approval_button');
        var student_id = $(this).closest('.student').data('student');
        $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify({"student_id":student_id}),
            success: updateStudents
        });
    });

    function responseCSV(result) {
        $('.masterclass-get-csv', element).text(result.button_text);
    }

    $(element).find('.masterclass-get-csv').bind('click', function () {
        var handlerUrl = runtime.handlerUrl(element, 'get_csv');
        $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify({"getcsv":"Yes"}),
            //success: responseCSV
        });
    });

}

