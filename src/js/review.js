(function($) {

    // Define "select" method when using these options.
    var autocompleteOptions = {
        minLength: 3,
        source: function(request, response) {
            var translationNoResults = $(this.element).data('translation-no-results');
            var translationTooManyResults = $(this.element).data('translation-too-many-results');
            // Ajax call to the user search view
            $.ajax({
                url: $(this.element).data('search-url'),
                dataType: 'json',
                data: {
                    name: request.term
                },
                success: function(data) {
                    var result = [];
                    if (data.success !== true) {
                        // Error
                        result = [
                            {
                                name: data.message,
                                username: ''
                            }
                        ];
                        return response(result);
                    }
                    if (!data.users.length) {
                        // No results
                        result = [
                            {
                                name: translationNoResults,
                                username: ''
                            }
                        ];
                        return response(result);
                    }
                    var res = data.users;
                    if (data.count > 10) {
                        // Too many results
                        res = res.slice(0, 10);
                        res.push({
                            name: translationTooManyResults,
                            username: ''
                        });
                    }
                    return response(res);
                }
            });
        },
        create: function() {
            // Prepare the entries to display the name and email address.
            $(this).data('ui-autocomplete')._renderItem = function (ul, item) {
                if (!item.name) {
                    item.name = item.first_name + ' ' + item.last_name;
                }
                return $('<li>')
                    .append('<a><strong>' + item.name + '</strong><br><i>' + item.username + '</i></a>')
                    .appendTo(ul);
            };
        },
        select: function(event, ui) {
            if (!ui.item.uid) {
                // No value (eg. when clicking "No results"), do nothing
                return false;
            }

            var displayContainer = $('#' + $(this).data('display-container'));
            var userInputFieldName = $(this).data('user-input-field');
            var maxUsers = $(this).data('max-users');
            var currentUserCount = getCurrentUserCount(displayContainer);

            if (maxUsers === undefined || currentUserCount < maxUsers) {
                addUserId(displayContainer, ui.item.uid, userInputFieldName);
                displayUser(displayContainer, ui.item.uid, ui.item.first_name,
                    ui.item.last_name);
            }
            
            if (maxUsers && currentUserCount + 1 >= maxUsers) {
                $(this).prop('disabled', true);
            }
        
            $(this).val('');
            return false;
        }
    };

    $('#review-search-user').autocomplete(autocompleteOptions);
    $('#review-change-compiler').autocomplete(autocompleteOptions);

    function displayUser(container, userId, userFirstName, userLastName) {
        container.append($('<div>').addClass('alert-box').html(userFirstName + ' ' + userLastName + '<a href="#" ' +
        'class="close" onclick="return reviewRemoveUser(this, ' + userId + ');">' +
        '&times;</a>'));
    }

    function addUserId(container, userId, userInputFieldName) {
        var input = container.find('[name="' + userInputFieldName + '"]');
        var ids = input.val().split(',').filter(function(n) { return n != "" });
        ids.push(userId);
        input.val(ids.join(','));
    }

    $('.js-toggle-edit-assigned-users').click(function() {
        // Toggle list/edit of assigned users
        $('#review-list-assigned-users').toggle();
        $('#review-edit-assigned-users').toggle();
        return false;
    });

})(jQuery);

function getCurrentUserCount(container) {
    return container.find('div.alert-box').length;
}

function reviewRemoveUser(el, userId) {
    var displayField = $(el).closest('.alert-box');
    var input = displayField.siblings('input:hidden');

    if (!input.length) {
        return false;
    }
    var ids = input.val().split(',').filter(function(n) {
        return n != "" && n != String(userId) });
    input.val(ids.join(','));

    var displayContainer = displayField.parent('.user-display');
    var searchField = displayContainer.siblings('input');
    var maxUsers = searchField.data('max-users');
    var currentUserCount = getCurrentUserCount(displayContainer);

    displayField.remove();
    
    if (maxUsers !== undefined && currentUserCount < maxUsers) {
        searchField.prop('disabled', false);
    }

    return false;
}
