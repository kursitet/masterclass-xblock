/* Javascript for MasterclassXBlock. */

function MasterclassXBlockStudio(runtime, element) {
    var saveUrl = runtime.handlerUrl(element, 'save_masterclass');
   
    var validators = {
        'number': function (x) {
            return Number(x);
        },
        'string': function (x) {
            return !x ? null : x;
        },
        'boolean': function (x) {
            return ["true", "yes", "1", "no", "false", "0"].indexOf(x.toLowerCase()) >= 0;
        }
    }

    $(element).find('.action-cancel').bind('click', function() {
      runtime.notify('cancel', {});
    });    

    $(element).find('.action-save').bind('click', function() {
        runtime.notify('save', {state: 'start'});

        var data = {};
        $(element).find("input").each(function (index, input) {
            data[input.name] = input.value;
        });

        $.post(saveUrl, JSON.stringify(data)).done(function(response) {
            runtime.notify('save', {state: 'end'});
            window.location.reload(false);
        });
        
        //$.ajax({
        //    type: "POST",
        //    url: saveUrl,
        //    data: JSON.stringify(data),
        //    success: function () {
        //        runtime.notify('save', {state: 'end'});
        //    }
        //});
    });

    return {
        save: save
    }
}
