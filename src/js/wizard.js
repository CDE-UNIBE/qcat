// WIZARD
// -----------------
// Next / Previous step

/**
 * Loop through the form fields of a subcategory to find out if they are
 * empty or if they contain values.
 *
 * @param {Element} element - An element containing the form fields, for
 *   example the subcategory fieldset.
 */
function hasContent(element) {
    var content = false;
    // Textfields and Textareas
    $(element).find('div.row.single-item input:text, div.row.single-item textarea').each(function () {
        if ($(this).is(":visible") && $(this).val() != '') {
            content = true;
            return;
        }
    });
    // Radio
    $(element).find('div.row.single-item input:radio').each(function () {
        if ($(this).is(':checked') && $(this).val() != '') {
            content = true;
            return;
        }
    });
    // Checkbox
    $(element).find('div.row.single-item input:checkbox').each(function () {
        if ($(this).is(':checked')) {
            content = true;
            return;
        }
    });
    // Image
    $(element).find('div.image-preview').each(function () {
        if ($(this).find('img').length) {
            content = true;
            return;
        }
    });
    // Select
    $(element).find('div.row.single-item select').each(function () {
        if ($(this).find(':selected').val()) {
            content = true;
            return;
        }
    });
    return content;
}


/**
 * Updates the process indicators while entering the form. Updates the
 * number of subcategories filled out and the progress bar.
 */
function watchFormProgress() {
    var completed = 0;
    $('fieldset.row').each(function () {
        // Check the content only for the parent fieldset.
        var hasParentFieldset = $(this).parent().closest('fieldset.row');
        if (!hasParentFieldset.length) {
            var content = hasContent(this);
            if (content) {
                completed++;
            }
        }
    });
    var stepsElement = $('.progress-completed');
    stepsElement.html(completed);
    var total = stepsElement.next('.progress-total').html();
    var progress = completed / total * 100;
    $('.wizard-header').find('.meter').width(progress + '%');

    // While we're at it, also check if "other" checkboxes are to be ticked
    $('input.checkbox-other').each(function () {
        var $el = $(this);
        if ($el.parent('label').find('input:text').val() != '') {
            $($el.prop('checked', true));
        }
        // Toggle readonly
        $el.closest('label').find('input:text').attr(
            'readonly', !$el.is(':checked'));
    });
    $('input.radio-other').each(function() {
        // Toggle readonly
        $(this).closest('label').find('input:text').attr(
            'readonly', !$(this).is(':checked'));
    });

    updateAutoMultiplication();
}

/**
 * Function to handle fields with [data-auto-multiplication] and
 * [data-auto-sum]. Such fields are currently used for the input tables.
 */
function updateAutoMultiplication() {
    var check_sum = false;
    $('[data-auto-multiplication]').each(function() {

        // Get the prefix of the current questiongroup
        var prefix_parts = this.name.split('-');
        var list_item = $(this).closest('.list-item');

        var sum = 1;
        var data_sum = $(this).data('auto-multiplication').split('|');
        for (var i in data_sum) {
            var el = list_item.find('input[name=' + prefix_parts[0] + '-' + prefix_parts[1] + '-' + data_sum[i] + ']');
            if (el.length == 0) {
                // Try to find with "original"
                el = list_item.find('input[name=' + prefix_parts[0] + '-' + prefix_parts[1] + '-original_' + data_sum[i] + ']');
            }
            sum *= parseFloat(el.val());
        }
        if (sum) {
            $(this).val(sum.toFixed(2));
        } else {
            $(this).val('');
        }
        check_sum = true;
    });
    if (check_sum) {
        $('[data-auto-sum]').each(function() {
            var identifier = $(this).data('auto-sum');
            var sum = 0;
            var has_value = false;
            $('input[name$=' + identifier + ']').each(function() {
                var x = parseFloat($(this).val());
                if (x) {
                    has_value = true;
                    sum += x;
                }
            });
            if (has_value) {
                $(this).val(sum.toFixed(2));
            } else {
                $(this).val('');
            }
        });
    }
}

/**
 * Check for additional questiongroups ("plus" questions) and hide them
 * initially if they are empty.
 */
function checkAdditionalQuestiongroups() {
    $('.plus-questiongroup div.content').each(function () {
        $(this).toggleClass('active', hasContent(this));
    });
}

/**
 * Check for questiongroups which are expanded only if a checkbox is
 * selected. Show them if they have some content.
 */
function checkCheckboxQuestiongroups() {
    $('.cb-toggle-questiongroup-content').each(function () {
        var qg = $(this).closest('.questiongroup');
        if (hasContent(qg)) {
            qg.find('.cb-toggle-questiongroup').click();
        }
    });
}

/**
 * Check if there are conditional questions which are to be shown or hidden.
 *
 * @param element - The question element (containing the input fields which
 * trigger changes and the question conditions as data attribute
 * ("data-question-conditions").
 */
function checkConditionalQuestions(element) {
    var $el = $(element),
        qg = $el.closest('.list-item'),
        conditions = $el.data('question-conditions'),
        input_elements = $el.find('input'),
        input_values = [];

    input_elements.each(function() {
        var input_type = input_elements.attr('type');
        if ((input_type == 'checkbox' || input_type == 'radio')
            && $(this).is(':checked')) {
            input_values.push(this.value);
        }
    });
    // Also add checkboxes if they are "checkbox_other".
    if ($el.hasClass('checkbox-other') && $el.is(':checked')) {
        input_values.push(true);
    }

    var cond_by_name = {};
    for (var i = 0; i < conditions.length; i++) {
        var condition_parts = conditions[i].split('|');
        try {
            cond_by_name[condition_parts[1]].push(condition_parts[0]);
        } catch (err) {
            cond_by_name[condition_parts[1]] = [condition_parts[0]];
        }
    }

    for (var cond_name in cond_by_name) {
        if (cond_by_name.hasOwnProperty(cond_name)) {
            var conditional_el = qg.find(
                '[data-question-condition="' + cond_name + '"]');
            var condition_fulfilled = false;
            for (var j = 0; j < cond_by_name[cond_name].length; j++) {
                var current_condition = cond_by_name[cond_name][j];

                for (var k = 0; k < input_values.length; k++) {
                    var val = input_values[k];
                    if (parseInt(val)) {
                        var e = val + current_condition;
                    } else {
                        var e = '"' + val + '"' + current_condition;
                    }
                    condition_fulfilled = condition_fulfilled || eval(e);
                }
            }

            conditional_el.toggle(condition_fulfilled);
            if (!condition_fulfilled) {
                clearQuestiongroup(conditional_el);
            }
        }
    }
}

/**
 * Checks conditional questiongroups and shows or hides questiongroups
 * based on an input value condition.
 *
 * @param {Element} element - The input element triggering the
 *   questiongroup.
 */
function checkConditionalQuestiongroups(element) {

    // Collect all the conditions for a questiongroup as they must all be
    // fulfilled and group them by questiongroup identifier.
    var condition_string = $(element).data('questiongroup-condition');
    var all_conditions = condition_string ? condition_string.split(',') : [];
    var conditionsByQuestiongroup = {};
    for (var i = all_conditions.length - 1; i >= 0; i--) {
        condition = all_conditions[i].split('|');
        if (condition.length !== 2) return;
        if (conditionsByQuestiongroup[condition[1]]) {
            conditionsByQuestiongroup[condition[1]].push(condition[0]);
        } else {
            conditionsByQuestiongroup[condition[1]] = [condition[0]];
        }
    }

    // Collect all the input fields with the same name, which is important
    // for example for checkboxes.
    allElements = $('[name="' + $(element).attr('name') + '"]');

    // For each conditional questiongroup, check if one of the form
    // elements with the given name fulfills all the conditions. If this
    // is true, then show the conditional questiongroup.
    for (var questiongroup in conditionsByQuestiongroup) {
        var currentConditions = conditionsByQuestiongroup[questiongroup];
        var currentConditionsFulfilled = false;

        allElements.each(function () {
            var currentElement = $(this);
            var val = null;

            var inputType = currentElement.attr('type');
            if ((inputType == 'radio' || inputType == 'checkbox') && currentElement.is(':checked')) {
                val = currentElement.val();
            } else if (inputType == 'text') {
                val = currentElement.val();
            }

            var conditionsFulfilled = val !== null && val !== '';
            if (val) {
                for (var c in currentConditions) {
                    if (parseInt(val)) {
                        var e = val + currentConditions[c];
                    } else {
                        var e = '"' + val + '"' + currentConditions[c];
                    }
                    conditionsFulfilled = conditionsFulfilled && eval(e);
                }
            }

            currentConditionsFulfilled = currentConditionsFulfilled || conditionsFulfilled;
        });

        var questiongroupContainer = $('#' + questiongroup),
            previousCondition = questiongroupContainer.data('conditions-fulfilled');
        questiongroupContainer.toggle(currentConditionsFulfilled);
        if (!currentConditionsFulfilled && previousCondition === true) {
            // Only clear questiongroup if it was previously visible as this is
            // an expensive function.
            clearQuestiongroup(questiongroupContainer);
        }
        // Store if the condition is now fulfilled, only if there were changes
        if (currentConditionsFulfilled != previousCondition) {
            questiongroupContainer.data(
                'conditions-fulfilled', currentConditionsFulfilled);
        }
    }
}


/**
 * Remove a linked questionnaire.
 * @param el - The button clicked, needs to be inside the questiongroup of the
 *   linked questionnaire.
 * @returns {boolean}
 */
function removeLinkedQuestionnaire(el) {
    var qg = $(el).closest('.list-item');

    // Empty the value field containing the link ID.
    qg.find('[name$=link_id]').val('');

    // Empty the preview container
    qg.find('.link-preview').empty().trigger('change');

    // Show the search field again
    qg.find('.link-search').show();

    return false;
}


/**
 * Shows the container with the preview of the added link. This assumes that the
 * name of the linked questionnaire is already set in the corresponding
 * container (.link-name).
 * @param qg
 */
function showLinkPreview(qg) {
    // Create the preview container
    var link_name = qg.find('.link-name').data('link-name');
    var preview_container = qg.find('.link-preview');
    preview_container.empty();
    preview_container.append(
        '<div class="alert-box secondary">' + link_name + '<a href="#" ' +
        'class="close" onclick="return removeLinkedQuestionnaire(this);">' +
        '&times;</a></div>'
    );

    // Hide the search
    qg.find('.link-search').hide();
}

// Initial questionnaire links - populate the preview container.
$('.select-link-id').each(function () {
    var $t = $(this);
    var qg = $t.closest('.list-item');
    var link_id = $t.val();
    if (link_id) {
        // A link is already selected, show it
        showLinkPreview(qg);
    }
});


/**
 * Clears all form fields of a questiongroup. It is important to trigger
 * the change event for each so chained conditional questiongroups are
 * validated.
 *
 * @param {Element} questiongroup - The questiongroup element in which
 *   to clear all fields.
 */
function clearQuestiongroup(questiongroup) {
    questiongroup.find('input:text, textarea').val('').change();
    questiongroup.find('input:radio').prop('checked', false).change();
    questiongroup.find('input:checkbox').prop('checked', false).change();
    questiongroup.find('select').prop('selectedIndex', 0).change();
    questiongroup.find('input:hidden.is-cleared').val('').change();
    questiongroup.find('.chosen-select').val('').trigger('chosen:updated');
}

$(function () {

    $('body')
    // LIST ITEM
    // -----------------
    // List item remove
        .on('click', '.list-item-action[data-remove-this]', function (e) {

            var qg = $(this).closest('.list-item').data('questiongroup-keyword');
            var currentCount = parseInt($('#id_' + qg + '-TOTAL_FORMS').val());
            var maxCount = parseInt($('#id_' + qg + '-MAX_NUM_FORMS').val());
            var minCount = parseInt($('#id_' + qg + '-MIN_NUM_FORMS').val());

            var item = $(this).closest('.list-item.is-removable');
            item.remove();
            var otherItems = $('.list-item[data-questiongroup-keyword="' + qg + '"]');
            if (otherItems.length <= minCount) {
                otherItems.find('[data-remove-this]').hide();
            }
            otherItems.each(function (i, el) {
                updateFieldsetElement($(el), qg, i);
            });

            currentCount--;
            $('#id_' + qg + '-TOTAL_FORMS').val(currentCount);
            $('.list-action [data-add-item][data-questiongroup-keyword="' + qg + '"]').toggle(currentCount < maxCount);

            watchFormProgress();

        })
        // List item add
        .on('click', '.list-action [data-add-item]', function (e) {

            var qg = $(this).data('questiongroup-keyword');
            var currentCount = parseInt($('#id_' + qg + '-TOTAL_FORMS').val());
            var maxCount = parseInt($('#id_' + qg + '-MAX_NUM_FORMS').val());

            if (currentCount >= maxCount) return;

            var container = $(this).closest('.list-action');

            var otherItems = $('.list-item[data-questiongroup-keyword="' + qg + '"]');
            otherItems.find('[data-remove-this]').show();

            var lastItem = container.prev('.list-item');
            var doNumberingUpdate = false;

            // If the item to clone is a table row, we need to find it inside
            // the table
            var isTableRow = typeof $(this).data('add-table-row') !== 'undefined';
            if (isTableRow) {
                lastItem = container.prev('.outer-list-item').find('.list-item:first-child');
                doNumberingUpdate = true;
            }

            if (!lastItem.length) {
                // The element might be numbered, in which case it needs to be
                // accessed differently
                if (container.parent('.questiongroup-numbered-prefix').length) {
                    lastItem = container.prev('.row');
                    doNumberingUpdate = true;
                }
            }
            if (!lastItem.length) return;

            // Destroy chosen selects before cloning the elements. Recreate the
            // chosen selects afterwards.
            var lastItemChosen = lastItem.find('.chosen-select');
            if (lastItemChosen.length) {
                lastItemChosen.chosen('destroy');
            }

            var newElement = lastItem.clone();

            updateFieldsetElement(newElement, qg, currentCount, true);

            if (isTableRow) {
                // Add table rows after the last existing row.
                newElement.insertAfter(container.prev('.outer-list-item').find('.list-item:last-child'));
            } else {
                newElement.insertBefore(container);
            }

            // Update the dropzones
            updateDropzones(true);

            updateChosen();

            currentCount++;
            $('#id_' + qg + '-TOTAL_FORMS').val(currentCount);
            $(this).toggle(currentCount < maxCount);

            if (doNumberingUpdate) {
                updateNumbering();
            }

            // Update the datepicker fields (need to remove "hasDatepicker"
            // first)
            if ($.fn.datepicker) {
                $('.date-input').each(function () {
                    $(this).toggleClass('hasDatepicker', false).datepicker(
                        $.extend(datepickerOptions, {
                            dateFormat: $(this).data('date-format')})
                    );
                });
            }

            // Update the autocomplete fields
            if ($.fn.autocomplete) {
                $('.user-search-field').autocomplete(userSearchAutocompleteOptions);
                $('.link-search-field').autocomplete(linkSearchAutocompleteOptions);
                $('.ui-autocomplete').addClass('medium f-dropdown');
                $(document).foundation();
                removeUserField(newElement);
            }

            // Remove any linked questionnaire of the new element - if necessary
            removeLinkedQuestionnaire(newElement);

            // Update question conditions
            newElement.find('[data-question-conditions]').trigger('change');

            // Update questiongroup conditions
            newElement.find('[data-questiongroup-condition]').trigger('change');
        })

        // Helptext: Toggle buttons (Show More / Show Less)
        .on('click', '.help-toggle-more', function (e) {
            var more = $(this).siblings('.help-content-more');
            var first = $(this).siblings('.help-content-first');
            if (more.is(':visible')) {
                // Hide "More"
                $(this).html($(this).data('text-more'));
                more.slideToggle(400, function () {
                    first.toggle();
                });
            } else {
                // Show "More"
                $(this).html($(this).data('text-first'));
                more.slideToggle();
                first.toggle();
            }
        })

        // ADD USERS
        // -----------------
        // Radio to switch between search registered or capture non-registered
        // person.
        .on('change', '.form-user-radio', function() {
            var qg = $(this).closest('.list-item');
            var select_user = qg.find('.form-user-tab-search');
            var create_user = qg.find('.form-user-tab-create');

            var selected = qg.find('input[name="form-user-radio"]:checked').val();
            if (selected === 'search') {
                select_user.show();
                create_user.hide();
            } else if (selected === 'create') {
                select_user.hide();
                create_user.show();
            } else {
                select_user.hide();
                create_user.hide();
            }
        })
        // Button to remove a selected user
        .on('click', '.form-user-selected a.close', function (e) {
            e.preventDefault();
            removeUserField($(this).closest('.list-item'));
        })
        // Remove selected users if new personas are entered
        .on('keyup', '.form-user-tab-create', function (e) {
            removeUserField($(this).closest('.list-item'), false);
        })

        // BUTTON BAR
        // -----------------
        // Button bar select line
        .on('click', '.button-bar', toggleButtonBarSelected)

        // RADIO BUTTONS
        // Deselectable radio buttons
        .on('click', 'input:radio', function () {
            var previousValue = $(this).attr('previousValue');
            var name = $(this).attr('name');
            var initiallyChecked = $(this).attr('checked');

            if (previousValue == 'checked' || (!previousValue && initiallyChecked == 'checked')) {
                $(this).removeAttr('checked');
                $(this).attr('previousValue', false);
                watchFormProgress();
                checkConditionalQuestiongroups(this);
            } else {
                $("input[name=" + name + "]:radio").attr('previousValue', false);
                $(this).attr('previousValue', 'checked');
            }

            if ($(this).data('has-other')) {
                // Click on a radio which has an "other" radio
                var $el = $(this);
                var keyword = $el.data('has-other');
                if ($el.is(':checked')) {
                    var list_item = $el.closest('.list-item');
                    // Deselect the "other" element if necessary
                    var other_radio = list_item.find('[data-other-radio=' + keyword + ']');
                    other_radio.attr('checked', false).attr('previousvalue', false);

                    // Reset the textfield
                    other_radio.closest('label').find('.radio-other-field').find('input').val('');
                }
            }
            if ($(this).hasClass('radio-other')) {
                // Click on a "other" radio
                $el = $(this);
                var keyword = $el.data('other-radio');
                var list_item = $el.closest('.list-item');
                if ($el.is(':checked')) {
                    // Deselect all other radio buttons of the group
                    list_item.find('input[data-has-other="' + keyword + '"]:radio')
                        .attr('checked', false).attr('previousvalue', false);
                } else {
                    $el.closest('label').find('.radio-other-field').find('input').val('');
                }
            }
            $(this).trigger('change');
        })

        // "Other" checkbox: Delete content of textfield if deselected
        .on('click', 'input:checkbox[class^="checkbox-other"]', function() {
            var $el = $(this);
            if (!$el.prop('checked')) {
                $el.closest('label').find('input:text').val('');
            }
            watchFormProgress();
        })

        // Validate max choices of checkboxes
        .on('change', '[data-cb-max-choices]', function() {
            var $t = $(this);
            if (this.checked) {
                var question = $t.closest('.single-item');
                if (!question.length) {
                    // Try to find on questiongroup level
                    var question = $t.closest('.list-item');
                }
                var checked = question.find('input[name="' + this.name + '"]:checked');
                if (checked.length > $t.data('cb-max-choices')) {
                    $(this).attr('checked', false);
                }
            }
        })

        // Conditional questions
        .on('change', '[data-question-conditions]', function() {
            checkConditionalQuestions(this);
        })
        .on('input', '[data-question-conditions]', function() {
            checkConditionalQuestions(this);
        })

        // Conditional questiongroups
        .on('change', '[data-questiongroup-condition]', function() {
            checkConditionalQuestiongroups(this);
        })
        .on('input', '[data-questiongroup-condition]', function() {
            checkConditionalQuestiongroups(this);
        })

        .on('click', '[data-checkbox-toggle]', function() {
            $(this).closest('div.columns').find(
                'div#' + $(this).data('checkbox-toggle')).slideToggle();
        })

        // Form progress upon input
        .on('change', 'fieldset.row div.row.single-item', function() {
            watchFormProgress();
        })

        .on('change', '[data-custom-to-options]', function() {
            var $t = $(this);
            var customToOption = $t.data('custom-to-options').replace(/'/g, '"');
            var keyKeyword = $t.data('key-keyword');
            var keyId = this.id;
            var currentValue = $t.val();

            try {
                var options = JSON.parse(customToOption);
            } catch(e) { return; }

            if (!options) return;
            
            var triggeredKeys = options['default'];
            if (options.hasOwnProperty(currentValue)) {
                triggeredKeys = options[currentValue];
            }

            Object.keys(triggeredKeys).forEach(function(key) {
                var val = triggeredKeys[key],
                    triggeredKeyEl = $('#' + keyId.replace(keyKeyword, key));

                if (!triggeredKeyEl.length) return;

                if (!Array.isArray(val) || val.length == 0) val = [""];

                if (val.length > 1) {

                    // If a previously selected value (eg. if page was newly
                    // loaded) is available, use this value if it is one of the
                    // available options. Else use the first available option.
                    var selectedValue = triggeredKeyEl.val();
                    if (!selectedValue || val.indexOf(selectedValue) == -1) {
                        selectedValue = val[0];
                    }
                    triggeredKeyEl.val(selectedValue);
                    triggeredKeyEl.prop('disabled', false);
                    
                    triggeredKeyEl.find('option').each(function() {
                        $(this).prop('disabled', val.indexOf(this.value) == -1)
                    });

                } else {
                    triggeredKeyEl.val(val[0]);
                    triggeredKeyEl.prop('disabled', true);
                }

                triggeredKeyEl.trigger('chosen:updated');
            });
        })

        .on('change', '[data-questiongroup-to-options]', function() {
            var $t = $(this),
                qg_to_options = $t.data('questiongroup-to-options').split(','),
                label = $t.data('questiongroup-to-options-label'),
                keyword = $t.data('questiongroup-to-options-keyword'),
                isOption = $t.data('questiongroup-to-options-is-option'),
                qgHasContent = hasContent(this);

            if (isOption && qgHasContent) return; // Values only changed

            qg_to_options.forEach(function(qg) {
                var qg_parts = qg.split('|');
                if (qg_parts.length != 2) return;

                var questiongroup = qg_parts[0],
                    question = qg_parts[1];

                var i = 0;
                do {
                    var id = '#id_' + questiongroup + '-' + i + '-' + question;
                    var select = $(id);

                    if (!select.length) break;

                    if (qgHasContent) {
                        select.append($('<option>', {
                            value: keyword,
                            text: label
                        }));
                        
                        // Temporarily store the selected value of the select
                        var selectedValue = select.val();

                        // Reorder the options
                        var optionsOrder = select.data('options-order').split(','),
                            firstOption = select.find('option:first'),
                            otherOptions = select.find('option:not(:first)');
                        otherOptions.sort(function(a,b){
                            var compA = $.inArray(a.value, optionsOrder),
                                compB = $.inArray(b.value, optionsOrder);
                            return (compA < compB) ? -1 : (compA > compB) ? 1 : 0;
                          });
                        select.html(otherOptions).prepend(firstOption);
                        select.val(selectedValue);

                    } else {
                        select.find('option[value="' + keyword + '"]').remove();
                    }
                    select.trigger('chosen:updated');
                    i++;
                }
                while ($(id).length);
            });
            $t.data('questiongroup-to-options-is-option', qgHasContent);
        })

        .on('click', '.cb-toggle-questiongroup', function () {
            var container = $(this).data('container');
            if ($(this).prop('checked')) {
                $('#' + container).slideDown();
            } else {
                $('#' + container).slideUp();
                // Clear the questiongroup
                clearQuestiongroup($(this).closest('.questiongroup'));
            }
        });

    // Initial form progress
    watchFormProgress();

    // Initially checked checkbox toggles.
    $('[data-checkbox-toggle]').each(function() {
        if (hasContent($(this).closest('div.columns'))) {
            $(this).trigger('click');
        }
    });

    // Trigger initial change for conditional questions
    $('[data-question-conditions]').trigger('change');

    // Trigger initial change for conditional questiongroups
    $('[data-questiongroup-condition]').trigger('change');

    // Trigger initial change for custom options (only if they have values)
    $('[data-custom-to-options]').each(function() {
        if (this.value) $(this).trigger('change');
    });

    // Initial button bar selected toggle
    $('.button-bar').each(toggleButtonBarSelected);

    // Initial cb questiongroups
    checkCheckboxQuestiongroups();

    checkAdditionalQuestiongroups();

    // Select inputs with chosen
    function updateChosen() {
        if ($.fn.chosen) {
            $(".chosen-select").chosen({
                width: '100%',
                search_contains: true
            }).on('change', function(evt, params) {
                // If there is a display field, populate it with the selected value
                var $t = $(this);
                if ($t.data('select-display-field')) {
                    var displayKey = $t.data('select-display-field');
                    var displayText = '';
                    if (params.selected) {
                        displayText = $t.find('option:selected').html();
                    }
                    // Find the display field: Replace the key in the element's ID
                    // with the key of the display field. Important: Replace only
                    // last occurrence of string as qg can contain the key.
                    var displayId = this.id.replace(
                        new RegExp($t.data('key-keyword') + '$'), displayKey);
                    var displayField = $('#' + displayId);
                    if (displayField.length) {
                        displayField.val(displayText);
                    }
                }
            });
        }
    }
    updateChosen();


    if ($.fn.datepicker) {
        var datepickerOptions = {
            changeMonth: true,
            changeYear: true
        };
        $('.date-input').each(function () {
            $(this).datepicker(
                $.extend(datepickerOptions, {
                    dateFormat: $(this).data('date-format')})
            );
        });
    }

    if ($.fn.sortable) {
        $('.sortable').sortable({
            handle: '.questiongroup-numbered-number',
            placeholder: 'sortable-placeholder',
            forcePlaceholderSize: true,
            stop: updateNumbering
        });
    }

    // Search a linked Questionnaire through AJAX autocomplete.
    if ($.fn.autocomplete) {
        /**
         * Options used when creating a new autocomplete to search and select
         * existing links.
         */
        var linkSearchAutocompleteOptions = {
            source: function (request, response) {
                var translationNoResults = $(this.element).data('translation-no-results');
                var translationTooManyResults = $(this.element).data('translation-too-many-results');
                var qg = $(this).closest('.list-item');
                qg.find('.form-link-search-error').hide();
                // AJAX call to the link search view
                $.ajax({
                    url: $(this.element).data('search-url'),
                    dataType: 'json',
                    data: {
                        q: request.term
                    },
                    success: function (data) {
                        if (!data.data.length) {
                            // No results
                            var result = [
                                {
                                    name: translationNoResults,
                                    code: ''
                                }
                            ];
                            response(result);
                        } else {
                            var res = data.data;
                            if (data.total > 10) {
                                // Too many results
                                res = res.slice(0, 10);
                                res.push({
                                    name: translationTooManyResults,
                                    code: ''
                                });
                            }
                            response(res);
                        }
                    }
                });
            },
            create: function () {
                // Prepare the entries to display the name and code.
                $(this).data('ui-autocomplete')._renderItem = function (ul, item) {
                    return $('<li>')
                        .append('<a><strong>' + item.name + '</strong><br><i>' + item.code + '</i></a>')
                        .appendTo(ul);
                };
            },
            select: function (event, ui) {
                if (!ui.item.value) {
                    // No value (eg. when clicking "No results"), do nothing
                    return false;
                }
                // First, make sure there is no other link with the same ID.
                var alreadyAdded = false;
                $('[name$=link_id]').each(function () {
                    if ($(this).val() == ui.item.value) {
                        alreadyAdded = true;
                    }
                });
                if (alreadyAdded) {
                    $(this).val('');
                    return false;
                }

                var qg = $(this).closest('.list-item');

                // Add ID of link
                qg.find('[name$=link_id]').val(ui.item.value).trigger('change');

                // Set the name
                qg.find('.link-name').data('link-name', ui.item.name);

                // Call the function to create the preview container
                showLinkPreview(qg);

                $(this).val('');
                return false;
            },
            minLength: 3
        };

        $('.link-search-field').autocomplete(linkSearchAutocompleteOptions);

        /**
         * Options used when creating a new autocomplete to search and select
         * existing users.
         */
        var userSearchAutocompleteOptions = {
            source: function (request, response) {
                var translationNoResults = $(this.element).data('translation-no-results');
                var translationTooManyResults = $(this.element).data('translation-too-many-results');
                var qg = $(this).closest('.list-item');
                qg.find('.form-user-search-error').hide();
                // AJAX call to the user search view
                $.ajax({
                    url: $(this.element).data('search-url'),
                    dataType: 'json',
                    data: {
                        name: request.term
                    },
                    success: function (data) {
                        if (data.success !== true) {
                            // Error
                            var result = [
                                {
                                    name: data.message,
                                    username: ''
                                }
                            ];
                            return response(result);
                        }
                        if (!data.users.length) {
                            // No results
                            var result = [
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
            create: function () {
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
            select: function (event, ui) {
                if (!ui.item.uid) {
                    // No value (eg. when clicking "No results"), do nothing
                    return false;
                }
                var qg = $(this).closest('.list-item');

                qg.find('.form-user-search').hide();
                qg.find('.form-user-search-loading').show();

                // Important: Clear only the content inside the tab, not the fields
                // above or below the tab.
                clearQuestiongroup(qg.find('.tabs-content'));
                updateUser(qg, ui.item.uid);

                // Hide empty message
                $(this).parent('fieldset').find('.empty').hide();

                $(this).val('');
                return false;
            },
            minLength: 3
        };

        $('.user-search-field').autocomplete(userSearchAutocompleteOptions);
        $('.link-search-field').autocomplete(linkSearchAutocompleteOptions);
        $('.ui-autocomplete').addClass('medium f-dropdown');

        // Initial user links
        $('.select-user-id').each(function () {
            $t = $(this);
            var qg = $t.closest('.list-item');
            if ($t.val()) {
                // A user is already selected, show it
                updateUser(qg, $t.val());
                // Also, select the radio to show it
                qg.find('input[value="search"]').click();
            } else {
                // No users linked but check if the form has content (new person)
                var initial_content = false;
                var input_fields = qg.find('.form-user-tab-create').find('input:text');
                input_fields.each(function () {
                    if ($(this).val() != '') {
                        initial_content = true;
                    }
                });
                qg.find('.form-user-search-loading').hide();
                if (initial_content) {
                    // Select the radio to show the content
                    qg.find('input[value="create"]').click();
                }
            }
        });
    }


    $('body').on('click', '[data-magellan-step]', function (e) {

        e.preventDefault();
        var expedition = $(this),
            hash = this.hash.split('#').join(''),
            target = $("a[name='" + hash + "']"),
            currentNumber = parseInt(hash.substr(hash.length - 1)),
            nextNumber = currentNumber,
            maxSteps = $("a[name^='question']").length;

        if (target.length != 0) {
            // Account for expedition height if fixed position
            var scroll_top = target.offset().top - 20 + 1;
            scroll_top = scroll_top - expedition.outerHeight();

            $('html, body').stop().animate({
                'scrollTop': scroll_top
            }, 700, 'swing', function () {
                if (history.pushState) {
                    history.pushState(null, null, '#' + hash);
                } else {
                    location.hash = '#' + hash;
                }
            });

            // Change Previous / Next href attr to point to the correct sections
            var nextNumber = currentNumber;
            if (currentNumber - 1 > 0) {
                previous = 'question' + (currentNumber - 1);
                $('[data-magellan-step="previous"]').attr('href', '#' + previous);
            }
            if (currentNumber < maxSteps) {
                next = 'question' + (currentNumber + 1);
                $('[data-magellan-step="next"]').attr('href', '#' + next);
            }
        }
    });

    updateDropzones();
});


/*
 * Fetch the user details from the database (with an update of the user details)
 * and display the id.
 */
function updateUser(qg, user_id) {
    // Copy the user to the local QCAT database if not yet there.

    var csrf = $('input[name="csrfmiddlewaretoken"]').val();
    $.ajax({
        url: qg.find('.user-search-field').data('update-url'),
        type: "POST",
        data: {
            uid: user_id
        },
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", csrf);
        },
        success: function (data) {
            if (data.success !== true) {
                qg.find('.form-user-search-error').html('Error: ' + data.message).show();
                return;
            }
            var userDisplayname = data.name;

            // Add the uid to the hidden input field
            qg.find('.select-user-id').val(user_id);
            qg.find('.select-user-display').val(userDisplayname);

            // Add user display field
            addUserField(qg, userDisplayname);

            qg.find('.form-user-search').hide();
        },
        error: function (response) {
            qg.find('.form-user-search-error').html('Error: ' + response.statusText).show();
        }
    });
}


/**
 * Add a display field for a selected user found through the search.
 */
function addUserField(qg, user_name) {
    qg.find('.form-user-search-loading').hide();
    var user = '<div class="alert-box secondary">' + user_name + '<a href="" class="close">&times;</a></div>';
    qg.find('.form-user-selected').html(user).show();
    qg.find('a.show-tab-select').click();
}


/**
 * Remove a display field for a selected user.
 */
function removeUserField(qg, focus) {
    qg.find('.form-user-selected').html('').hide();
    if (focus !== false) {
        qg.find('a.show-tab-select').click();
    }
    qg.find('.form-user-search').show();
    qg.find('.select-user-id').val('');
    qg.find('.select-user-display').val('');
}


/**
 * DropzoneJS file upload.
 */
var dropzones = [];
function updateDropzones(emptyNew) {
    $('.dropzone').each(function () {

        // If there is already a dropzone attached to it, do nothing.
        if (this.dropzone) return;

        var dropzoneContainer = $(this);
        var previewContainer = $(this).data('upload-preview-container');
        if (previewContainer) {
            previewContainer = $('#' + previewContainer);
            previewContainer.on('mouseover', function () {
                $(this).find('.remove-image').toggle(true);
            }).on('mouseout', function () {
                $(this).find('.remove-image').toggle(false);
            });

            previewContainer.find('.remove-image').click(function () {
                /**
                 * It is necessary to find the correct dropzone as there can be
                 * multiple on the same page.
                 */
                var dropzone = null;

                var dropzoneId = $(this).closest('.single-item').find('.dropzone').attr('id');
                for (var d in dropzones) {
                    if (dropzones[d].element.id === dropzoneId) {
                        dropzone = dropzones[d];
                    }
                }

                if (dropzone) {
                    var files = dropzone.files;
                    for (var f in files) {
                        dropzone.removeFile(files[f]);
                    }
                    previewContainer.toggle();
                    dropzoneContainer.toggle();
                    previewContainer.find('.image-preview').empty();

                    // Manually reset the hidden form field if there is no file left.
                    if (files.length == 0) {
                        $('input#' + dropzone.element.id.replace('file_', '')).val('');
                    }
                }

                watchFormProgress();
                return false;
            });
        }

        var url = dropzoneContainer.data('upload-url');
        var csrf = $('input[name="csrfmiddlewaretoken"]').val();

        if (!url) {
            return;
        }

        var dz = new Dropzone(this, {
            url: url,
            addRemoveLinks: true,
            init: function () {
                dropzones.push(this);
                $(this.hiddenFileInput).attr(
                    'id', this.element.id.replace('file_', 'hidden_'));
                if (previewContainer) {
                    var el = $('input#' + this.element.id.replace('file_', ''));
                    if (el.val()) {

                        $.ajax({
                            url: '/questionnaire/file/interchange/' + el.val()
                        }).done(function (interchange) {
                            addImage(previewContainer, dropzoneContainer, interchange);
                            watchFormProgress();
                        });
                    }
                }
            },
            sending: function (file, xhr, formData) {
                xhr.setRequestHeader("X-CSRFToken", csrf);
            },
            success: function (file, response) {
                if (previewContainer && response['interchange']) {
                    addImage(previewContainer, dropzoneContainer,
                        response['interchange']);
                }
                watchFormProgress();
                addFilename(response['uid'], file, this);
            },
            error: function (file, response) {
                this.removeFile(file);
                watchFormProgress();
                showUploadErrorMessage(response['msg']);
            },
            removedfile: function (file) {
                removeFilename(file, this);
                var _ref;
                return (_ref = file.previewElement) != null ? _ref.parentNode.removeChild(file.previewElement) : void 0;
            }
        });

        if (emptyNew === true) {
            $('input#' + dz.element.id.replace('file_', '')).val('');
        }
    });
}

/**
 * Add an image to the preview container. This is done by creating an
 * image element and adding the interchange attribute.
 *
 * @param {element} previewContainer - The preview container to add the
 *   image to. This element will be made visible.
 * @param {element} dropzoneContainer - The dropzone container which
 *   will be hidden.
 * @param {string} interchangeData - The interchange data.
 */
function addImage(previewContainer, dropzoneContainer, interchangeData) {
    var img = $(document.createElement('img'));
    img.attr('data-interchange', interchangeData);
    img.css({'width': '100%'});
    previewContainer.find('.image-preview').html(img);
    $(document).foundation();
    $(document).foundation('interchange', 'reflow');
    dropzoneContainer.toggle();
    previewContainer.toggle();
}

/*
 * Add a filename to the hidden form input field after upload of the
 * file. Also stores the filename to the file so it can later be
 * retrieved.
 *
 * @param {string} filename - The filename of the uploaded file as
 *  returned by the server.
 * @param {file} file - The uploaded file.
 * @param {Element} dropzone - The dropzone element.
 */
function addFilename(filename, file, dropzone) {
    file.filename = filename;
    var el = $('input#' + dropzone.element.id.replace('file_', ''));
    var vals = [];
    if (el.val()) {
        vals = el.val().split(',');
    }
    vals.push(filename);
    el.val(vals.join(','));
}

/*
 * Remove a filename from the hidden form input field after removing the
 * file from the dropzone.
 *
 * @param {file} file - The file to be removed.
 * @param {Element} dropzone - The dropzone element.
 */
function removeFilename(file, dropzone) {
    var el = $('input#' + dropzone.element.id.replace('file_', ''));
    var vals = [];
    if (el.val()) {
        vals = el.val().split(',');
    }
    for (var v in vals) {
        if (vals[v] == file.filename) {
            vals.splice(v, 1);
        }
    }
    el.val(vals.join(','));
}

/*
 * Show an error message if the file upload failed.
 *
 * @param {string} message - The error message returned by the server if
 *  available.
 */
function showUploadErrorMessage(message) {
    if (message) {
        alert('Error: ' + message);
    } else {
        alert('An error occurred while uploading the file.');
    }
}


/**
 * Toggles CSS class "is-selected" for button bars. If a value is
 * selected, the row is highlighted. If no value (empty string or '') is
 * selected, it is not.
 *
 * $(this): div.button-bar
 */
function toggleButtonBarSelected() {
    var selectedValue = $(this).find('input[type="radio"]:checked').val();
    var item = $(this).closest('.list-item');
    if (item.is('tr')) {
        // Do not add class "is-selected" to <tr> elements as this will break
        // the layout of the table.
        return;
    }
    if (selectedValue && selectedValue != 'none' && selectedValue != '') {
        item.addClass('is-selected');
    } else {
        item.removeClass('is-selected');
    }
    // item.toggleClass('is-selected', !(!selectedValue || 0 === selectedValue.length));
}


/**
 * Updates elements of a form fieldset. Fields of a Django formset are
 * named "[prefix]-[index]-[fieldname]" and their ID is
 * "id_[prefix]-[index]-[fieldname]". When adding or removing elements
 * of a fieldset, the name and index need to be updated.
 *
 * This function udates the name and id of each input field inside the
 * given fieldset element. It also updates the "label-for" attribute for
 * any label found inside the given element.
 *
 * Use this function to correctly label newly added fields of a
 * questiongroup ("Add more") or to re-label the remaining fields after
 * removing a field from a questiongroup ("Remove").
 *
 * @param {Element} element - The form element.
 * @param {string} prefix - The prefix of the questiongroup.
 * @param {integer} index - The index of the element.
 * @param {boolean} reset - Whether to reset the values of the input
 * fields or not. Defaults to false (do not reset the values).
 */
function updateFieldsetElement(element, prefix, index, reset) {
    reset = (typeof reset === "undefined") ? false : true;
    var id_regex = new RegExp('(' + prefix + '-\\d+-)');
    var replacement = prefix + '-' + index + '-';
    element.find(':input').each(function () {
        // Dropzone input button needs to be treated differently. Update all
        // the field references and reset the image container if necessary.
        if ($(this).data('dropzone-id')) {
            var old_dz_id = $(this).data('dropzone-id');
            var new_dz_id = old_dz_id.replace(id_regex, replacement);
            var row = $(this).closest('.single-item');
            var dz_container = row.find('#' + old_dz_id);

            dz_container.attr({
                'id': new_dz_id,
                'data-upload-preview-container': 'preview-' + new_dz_id
            });
            row.find('#preview-' + old_dz_id).attr({'id': 'preview-' + new_dz_id});
            if (reset) {
                dz_container.html('<div class="fallback">Sorry, no upload functionality right now.</div>');
                row.find('.image-preview').html('');
            }
            row.find('.remove-image').attr({'data-dropzone-id': new_dz_id});
        } else {
            if ($(this).attr('name') && $(this).attr('id')) {
                var name = $(this).attr('name').replace(id_regex, replacement);
                var id = $(this).attr('id').replace(id_regex, replacement);
                $(this).attr({'name': name, 'id': id});
            }
        }
    });
    element.find('label').each(function () {
        var for_attr = $(this).attr('for');
        if (for_attr) {
            var newFor = for_attr.replace(id_regex, replacement);
            $(this).attr('for', newFor);
        }
    });

    if (reset) {
        clearQuestiongroup(element);
        element.find('.form-user-tab-search').hide();
        element.find('.form-user-tab-create').hide();
    }
}


/**
 * Toggle the conditional image checkboxes if the parent checkbox was
 * clicked. If deselected, all conditional checkboxes are unchecked.
 *
 * el: div of conditional image checkboxes
 */
function toggleImageCheckboxConditional(el) {
    var topCb = el.parent('.list-gallery-item').find('input[data-toggle]');
    if (!topCb.is(':checked')) {
        el.find('input').removeAttr('checked')
    }
}
