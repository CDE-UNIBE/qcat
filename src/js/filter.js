$(function() {

  // Initially update the filter input fields
  updateFilterInputs();

  // Button to remove a filter. As the filter buttons are added
  // dynamically, the event needs to be attached to an element which is
  // already there.
  $('body').on('click', 'a.remove-filter', function () {
    var $t = $(this);

    var p = removeFilter($t.data('questiongroup'), $t.data('key'), $t.data('value'));

    // Always delete the paging parameter if the filter was modified
    delete p['page'];

    var s = ['?', $.param(p, traditional=true)].join('');
    changeUrl(s);
    updateList(s);
    updateFilterInputs();

    return false;
  });

  // Button to reset all filters
  $('body').on('click', '#filter-reset', function() {

    var p = parseQueryString();

    // Remove all filter parameters
    p = removeFilterParams(p);

    // Always delete the paging parameter if the filter was modified
    delete p['page'];

    var s = ['?', $.param(p, traditional=true)].join('');
    changeUrl(s);
    updateList(s);
    updateFilterInputs();
    return false;
  });

  // Button to submit the filter
  $('#submit-filter').click(function() {
    var p = parseQueryString();

    // Remove all filter parameters
    p = removeFilterParams(p);

    // Checkboxes
    $('#search-advanced input:checkbox').each(function() {
      var $t = $(this);
      if ($t.is(':checked')) {
        p = addFilter(p, $t.data('questiongroup'), $t.data('key'), $t.data('value'));
      }
    });

    // Sliders
    $('.nstSlider').each(function() {
      var qs = $(this).data('keyword');
      var min_val = $(this).parent().find('.min').val();
      var max_val = $(this).parent().find('.max').val();
      var min = $(this).data('cur_min');
      var max = $(this).data('cur_max');
      if (qs && min_val && max_val && !(min == min_val && max == max_val)) {
        p = addFilter(p, null, qs, [min_val, max_val].join('-'));
      }
    });

    // Always delete the paging parameter if the filter was modified
    delete p['page'];

    var s = ['?', $.param(p, traditional=true)].join('');
    changeUrl(s);
    updateList(s);
    return false;
  });

  $('body').on('click', '#pagination a', function() {
    var s = $(this).attr('href');
    changeUrl(s);
    updateList(s);
    return false;
  });

  // Slider
  // -----------------
  // See full doc here: http://lokku.github.io/jquery-nstslider/
  $('.nstSlider.filter-created').nstSlider({
    "crossable_handles": false,
    "left_grip_selector": ".leftGrip.filter-created",
    "right_grip_selector": ".rightGrip.filter-created",
    "value_bar_selector": ".bar.filter-created",
    "value_changed_callback": function(cause, leftValue, rightValue, prevLeft, prevRight) {
      $(this).parent().find('.leftLabel.filter-created').text(leftValue);
      $(this).parent().find('.rightLabel.filter-created').text(rightValue);
      $(this).parent().find('.min.filter-created').val(leftValue);
      $(this).parent().find('.max.filter-created').val(rightValue);
    }
  });
  $('.nstSlider.filter-updated').nstSlider({
    "crossable_handles": false,
    "left_grip_selector": ".leftGrip.filter-updated",
    "right_grip_selector": ".rightGrip.filter-updated",
    "value_bar_selector": ".bar.filter-updated",
    "value_changed_callback": function(cause, leftValue, rightValue, prevLeft, prevRight) {
      $(this).parent().find('.leftLabel.filter-updated').text(leftValue);
      $(this).parent().find('.rightLabel.filter-updated').text(rightValue);
      $(this).parent().find('.min.filter-updated').val(leftValue);
      $(this).parent().find('.max.filter-updated').val(rightValue);
    }
  });
});


/**
 * Update the filter input fields based on the currently active filter.
 */
function updateFilterInputs() {
  var p = parseQueryString();

  // Uncheck all input fields first
  $('input[data-questiongroup]').prop('checked', false);

  // Reset Sliders
  $('.nstSlider').each(function() {
    var min = $(this).data('range_min');
    var max = $(this).data('range_max');
    try {
      $(this).nstSlider('set_position', min, max);
    } catch(e) {}
  });

  for (var k in p) {
    var args = parseKeyParameter(k);
    if (args.length !== 2) continue;

    var values = p[k];
    for (var v in values) {
      var el = $('input[data-questiongroup="' + args[0] + '"][data-key="' + args[1] + '"][data-value="' + values[v] + '"]');
      if (el.length !== 1) continue;
      el.prop('checked', true);
    }
  }

  for (var k in p) {
    if (k != 'created' && k != 'updated') continue;

    $('.nstSlider').each(function() {
      var kw = $(this).data('keyword');
      if (kw != k) return;

      var values = p[k];
      if (values.length != 1) return;

      var years = values[0].split('-');
      if (years.length != 2) return;

      try {
        $(this).nstSlider('set_position', years[0], years[1]);
      } catch(e) {
        $(this).data('cur_min', years[0]);
        $(this).data('cur_max', years[1]);
      }
    });
  }
}


/**
 * Add an additional filter to the existing ones.
 *
 * @param {object} p - The object containing the query parameters.
 * @param {string} questiongroup - The keyword of the questiongroup. If
 *   null, only the key is used as parameter.
 * @param {string} key - The keyword of the key.
 * @param {string} value - The keyword of the value.
 * @return {object} An object with the updated query parameters.
 */
function addFilter(p, questiongroup, key, value) {
  var keyParameter = key;
  if (questiongroup) {
    keyParameter = createKeyParameter(questiongroup, key);
  }
  if (keyParameter in p) {
    p[keyParameter].push(value);
  } else {
    p[keyParameter] = [value];
  }
  return p;
}

/**
 * Remove a filter from the list of existing ones. Does nothing if the
 * filter does not exist.
 *
 * @param {string} questiongroup - The keyword of the questiongroup.
 * @param {string} key - The keyword of the key.
 * @param {string} value - The keyword of the value.
 * @return {object} An object with the updated query parameters.
 */
function removeFilter(questiongroup, key, value) {
  var keyParameter;
  if (key == '_search') {
    keyParameter = 'q';
  } else if (key == 'created' || key == 'updated') {
    keyParameter = key;
  } else {
    keyParameter = createKeyParameter(questiongroup, key);
  }
  var p = parseQueryString();
  if (keyParameter in p) {
    var i = p[keyParameter].indexOf(value);
    if (i > -1) {
      p[keyParameter].splice(i, 1);
    }
  }
  return p;
}

/**
 * Update the list based on the filter. Show a loading indicator and
 * send the filter through an AJAX request. If successful, update the
 * list and the active filters as well as the pagination. Hide the
 * loading indicator.
 *
 * @param {string} queryParam - The query parameter string to be
 * attached to the AJAX url.
 */
function updateList(queryParam) {
  var url = $('#search-advanced').data('url');
  if (typeof(url) == "undefined") {
    return;
  }

  $('.loading-indicator').show();
  $.ajax({
    url: [url, queryParam].join(''),
    type: 'GET',
    success: function(data) {
      $('#questionnaire-list').html(data.list);
      $('#active-filters').html(data.active_filters);
      $('#pagination').html(data.pagination);
      $('.loading-indicator').hide();
    },
    error: function(data) {
      alert('Something went wrong');
      $('.loading-indicator').hide();
    }
  });
}

/**
 * Update the URL of the browser without refreshing the page. If the
 * browser does not support this HTML5 feature, do a redirect to the
 * given URL
 *
 * @param {string} url - The new URL.
 */
function changeUrl(url) {
  if (typeof (history.pushState) != "undefined") {
    history.pushState(null,"", url);
  } else {
    window.location = url;
  }
}

/**
 * Delete all filter parameters from the query string.
 *
 * @param {object} p - The object containing the query parameters.
 * @return {object} The updated object with the query parameters.
 */
function removeFilterParams(p) {
  for (var k in p) {
    if (k.lastIndexOf('filter__', 0) === 0 || k == 'created' || k == 'updated') {
      delete p[k];
    }
  }
  return p;
}

/**
 * The reverse function of ``parseKeyParameter``.
 *
 * Helper function to create the string needed as query parameter for a
 * filter.
 *
 * The current format is:
 * filter__[questiongroup]__[key]
 *
 * Example:
 * filter__qg_11__key_14
 *
 * @param {string} questiongroup - The keyword of the questiongroup.
 * @param {string} key - The keyword of the key.
 * @return {string} The query parameter string.
 */
function createKeyParameter(questiongroup, key) {
  return ['filter', questiongroup, key].join('__');
}

/**
 * The reverse function of ``createKeyParameter``.
 *
 * Helper function to extract the questiongroup and key from the filter
 * parameter.
 *
 * @param {string} param - The filter parameter.
 * @return {array} An array containing the [0] questiongroup and [1] key
 * of the parameter. If not in the valid format, an empty array is
 * returned.
 */
function parseKeyParameter(param) {
  var parsed = param.split('__');
  if (parsed.length !== 3) return [];
  return [parsed[1], parsed[2]];
}

/**
 * Helper function to extract the query string from the URL. Can handle
 * repeating keys. Returns an object with values as arrays.
 * http://codereview.stackexchange.com/a/10396
 */
function parseQueryString() {
  var query = (location.search || '?').substr(1),
      map   = {};
  query.replace(/([^&=]+)=?([^&]*)(?:&+|$)/g, function(match, key, value) {
      (map[key] = map[key] || []).push(value);
  });
  return map;
}