(function($) {
    $.fn.bindModuleActions = function(options) {

        var defaults = {};
        var settings = $.extend({}, defaults, options);
        var elem = this;

        var loadingIndicator = $('#modules-available').contents();
        
        // A questionnaire was selected, check the available modules
        elem.on('change', '#input_questionnaire_id', function() {
            toggleModules(true);
            $.ajax({
                url: settings.checkUrl,
                method: 'POST',
                data: {
                    'csrfmiddlewaretoken': settings.csrfToken,
                    'configuration': settings.questionnaireConfiguration,
                    'link_id': get_questionnaire_id()
                }
            }).done(function(data) {
                // Show the modules loaded. Also initialize tooltips.
                $('#modules-available').html(data);
                $(document).foundation();
            });
        });

        // A selected questionnaire was removed, hide the further steps.
        elem.on('change', '.link-preview', function() {
            if (!$(this).val()) {
                toggleModules(false);
                toggleCreate(false);
            }
        });

        // A module was (de)selected, show/hide the next step.
        elem.on('change', 'input[name="module"]', function() {
            toggleCreate($(this).is(':checked'));
        });

        // The inline form (when viewing the details of a questionnaire). The
        // questionnaire is already selected.
        elem.on('click', '.js-show-embedded-modules-form', function() {
            $('.module-form-embedded-container').show();
            // Trigger a change to show the next step.
            $('#input_questionnaire_id').trigger('change');
            return false;
        });

        function get_questionnaire_id() {
            return $('#input_questionnaire_id').val();
        }

        function toggleModules(isVisible) {
            $('#modules-select-module').toggle(isVisible);
            showModulesLoading();
        }

        function toggleCreate(isVisible) {
            $('#modules-create').toggle(isVisible);
        }

        function showModulesLoading() {
            $('#modules-available').html(loadingIndicator);
        }
    };

}(jQuery));
