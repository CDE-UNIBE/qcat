(function ($) {
    $.fn.bindNotificationActions = function(options) {

        var defaults = {
            initialParams: '',
            questionnaire: '',
            isTeaser: false,
            isPending: false,
            isUnRead: false
        };
        var settings = $.extend({}, defaults, options);
        var elem = this;
        var page = 1;
        var statuses = [];

        // load initial data
        elem.load(settings.notificationsUrl + settings.initialParams, function() {
            showTooltips();
        });

        // load data when clicking on pagination item
        elem.on('click', 'ul.pagination li a', function(event) {
            page = $(this).attr('href');
            loadContent();
            return false;
        });

        // update 'is read' status on click
        elem.on('click', '.mark-done', function(event) {
            $.ajax({
                url: settings.readUrl,
                method: 'POST',
                data: ({
                    csrfmiddlewaretoken: settings.csrfToken,
                    user: settings.user,
                    log: $(this).val(),
                    checked: $(this).is(':checked')
                })
            }).done(function () {
                $(event.target).closest('.notification-list').toggleClass('is-read');
            });
        });

        // filter for 'isPending' and 'isRead'
        addFilter('#is-pending', 'isPending');
        addFilter('#is-unread', 'isUnRead');

        // filters for pending and questionnaires
        elem.on('click', '#questionnaire-filter-toggler', function() {
            $('#questionnaire-filter').toggle(
            function() {
                $(this).addClass('hide');
            }, function() {
                var select = $(this).children('select').first();
                // only load options if not in dom already - two options may be
                // present already ('all' and selected element).
                if (select.children('option').length < 3) {
                    $.ajax({
                        url: settings.questionnairesUrl,
                        method: 'get',
                        contentType: 'json'
                    }).done(function(data) {
                        $.each(data['questionnaires'], function(i, questionnaire) {
                            select.append(
                                '<option value="' + questionnaire + '">' +
                                questionnaire + '</option>'
                            );
                        });
                        select.chosen();
                        select.on('change', function(evt, params) {
                            page = 1;
                            settings.questionnaire = params['selected'];
                            loadContent();
                        });
                    });
                }
                $(this).removeClass('hide');
            });
        });

        // filters for statuses (actions)
        elem.on('click', '#status-filter-submit', function() {
            statuses = $('#status-dropdown input:checked').map(function() {
                return this.value;
            }).get();
            loadContent();
        });

        /**
         * Helper for 'toggle' filter elements (pending, is_unread).
         * @param selector
         * @param flagName
         */
        function addFilter(selector, flagName) {
            elem.on('click', selector, function() {
                elem.html(settings.spinner);
                settings[flagName] = ! $(this).hasClass('is-active-filter');
                page = 1;
                loadContent();
            });
        }

        /**
         * Helper to create the proper url depending on state of 'pending'
         * and 'questionnaire'
         * @returns {string}
         */
        function get_url() {
            var url = settings.notificationsUrl + '?page=' + page;

            if (settings.isTeaser) url += '&is_teaser';

            var isPendingDOM = $('#is-pending').hasClass('is-active-filter');
            if (settings.isPending || isPendingDOM) url += '&is_pending';

            var isUnReadDOM = $('#is-unread').hasClass('is-active-filter');
            if (settings.isUnRead || isUnReadDOM) url += '&is_unread';

            if (statuses != []) url += '&statuses=' + statuses.join(',');

            if (settings.questionnaire != '') {
                url += '&questionnaire=' + settings.questionnaire;
            }
            return url
        }

        /**
         * Foundations tooltips are appended to the body. This can be changed
         * with the options-attribute: append_to. However, this leads to faulty
         * display of the tips. Therefore remove old tips before loading the new
         * ones.
         */
        function showTooltips() {
            $('span[role="tooltip"]').remove();
            elem.foundation();
        }

        /**
         * Reload content with fresh params.
         */
        function loadContent() {
            $.ajax({
                url: get_url(),
                method: 'GET'
            }).done(function(data) {
                elem.html(data);
                showTooltips();
            });
        }
    };
}(jQuery));
