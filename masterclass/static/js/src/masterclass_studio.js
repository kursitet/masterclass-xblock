/* Javascript for MasterclassXBlock. */

function MasterclassXBlockStudio(runtime, element, server) {
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

    function save() {
        var view = this;
        view.runtime.notify('save', {state: 'start'});

        var data = {};
        $(element).find("input").each(function (index, input) {
            data[input.name] = input.value;
        });

        $.ajax({
            type: "POST",
            url: saveUrl,
            data: JSON.stringify(data),
            success: function () {
                view.runtime.notify('save', {state: 'end'});
            }
        });
    }

    return {
        save: save
    }
}
