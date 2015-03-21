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
        'date_string': function (x) {
            if ($.type(x) === "string") {
                var components = x.split("-");
                if (components.length != 3) return "";
                if (components[0].length != 4 || !$.isNumeric(components[0])) return "";
                if (components[1].length != 2 || !$.isNumeric(components[1])) return "";
                if (components[2].length != 2 || !$.isNumeric(components[2])) return "";
                return x;
            } else return "";
        },
        'boolean': function (x) {
            return ["true", "yes", "1", "no", "false", "0"].indexOf(x.toLowerCase()) >= 0;
        }
    };

    function save() {
        var view = this;
        view.runtime.notify('save', {state: 'start'});

        var data = {};
        $(element).find("input").each(function(index, input) {
            data[input.name] = input.value;
        });

        $.ajax({
            type: "POST",
            url: saveUrl,
            data: JSON.stringify(data),
            success: function() {
                view.runtime.notify('save', {state: 'end'});
            }
        });
    }

    return {
        save: save
    }
}
