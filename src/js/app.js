$(document).foundation({
    equalizer: {
        equalize_on_stack: true
    },
    interchange: {
        named_queries: {
            smallretina: 'only screen and (min-width: 1px) and (-webkit-min-device-pixel-ratio: 2), only screen and (min-width: 1px) and (min--moz-device-pixel-ratio: 2), only screen and (min-width: 1px) and (-o-min-device-pixel-ratio: 2/1), only screen and (min-width: 1px) and (min-device-pixel-ratio: 2), only screen and (min-width: 1px) and (min-resolution: 192dpi), only screen and (min-width: 1px) and (min-resolution: 2dppx)',
            mediumretina: 'only screen and (min-width: 641px) and (-webkit-min-device-pixel-ratio: 2), only screen and (min-width: 641px) and (min--moz-device-pixel-ratio: 2), only screen and (min-width: 641px) and (-o-min-device-pixel-ratio: 2/1), only screen and (min-width: 641px) and (min-device-pixel-ratio: 2), only screen and (min-width: 641px) and (min-resolution: 192dpi), only screen and (min-width: 641px) and (min-resolution: 2dppx)',
            largeretina: 'only screen and (min-width: 1025px) and (-webkit-min-device-pixel-ratio: 2), only screen and (min-width: 1025px) and (min--moz-device-pixel-ratio: 2), only screen and (min-width: 1025px) and (-o-min-device-pixel-ratio: 2/1), only screen and (min-width: 1025px) and (min-device-pixel-ratio: 2), only screen and (min-width: 1025px) and (min-resolution: 192dpi), only screen and (min-width: 1025px) and (min-resolution: 2dppx)'
        }
    },
    tab: {
      callback : function (tab) {
        // (Re-)apply equalizer
        $(document).foundation('equalizer', 'reflow');
      }
    }
});


var sourceSwap = function () {
    var $this = $(this);
    var newSource = $this.data('alt-src');
    $this.data('alt-src', $this.attr('src'));
    $this.attr('src', newSource);
};

// Replace svg with png if no svg
if (!Modernizr.svg) {
    $('img[src$=".svg"]').each(function () {
        //E.g replaces 'logo.svg' with 'logo.png'.
        $(this).attr('src', $(this).attr('src').replace('.svg', '.png'));
    });
}


/**
 * Update the numbering of the questiongroups.
 */
function updateNumbering() {
    $('.questiongroup-numbered-inline').each(function () {
        var counter = 0;
        $(this).find('.row.list-item').each(function () {
            counter++;
            $(this).find('label').each(function () {
                var label = $(this).html();
                $(this).html(counter + ': ' + label);
            });
        });
    });
    $('.questiongroup-numbered-prefix').each(function () {
        var counter = 1;
        $(this).find('input[id$=__order]').each(function () {
            $(this).val(counter++);
        });
        counter = 1;
        $(this).find('.questiongroup-numbered-number').each(function () {
            $(this).html(counter++ + ':');
        });
    });
    $('.questiongroup-numbered-table').each(function() {
        var counter = 1;
        $(this).find('.numbered-cell').each(function() {
            $(this).html(counter++ + '.');
        });
    });
}


$(function () {

    $('#submit-search').click(function(e) {
        // For the search on the landing page, do not submit the search
        // parameter (q) if it is empty.
        e.preventDefault();
        var form = $(this).closest('form');
        var search_field = form.find('input[name="q"]');
        if (!search_field.val()) {
            search_field.prop('disabled', 'disabled');
        }
        form.submit();
    });

    // Context switcher (WOCAT vs. Approaches vs. Technologies)
    $('.search-switch.button-switch input').click(function () {
        window.location = $(this).data('url');
    });

    $('img[data-alt-src]').each(function () {
        new Image().src = $(this).data('alt-src');
    }).hover(sourceSwap, sourceSwap);


    // UTILITIES
    // -----------------
    // Toggle view
    $('body')
        .on('click', '[data-toggle]', function (e) {
            var target = $('#' + $(this).data('toggle'));
            if ($(this).parent().hasClass('list-gallery-item')
                || $(this).parent().parent().hasClass('list-gallery-item')) {
                target.slideToggle();
                toggleImageCheckboxConditional(target);
            } else if ($(this).parent().hasClass('button-bar')) {
                var selectedValue = $(this).find('input[type="radio"]:checked').val();
                var item = $(this).closest('.list-item');
                if (selectedValue != 'none' && !item.hasClass('is-selected')) {
                    target.slideToggle();
                }
                if (selectedValue === 'none' && item.hasClass('is-selected')) {
                    target.slideToggle();
                }
            } else {
                e.preventDefault();
                target.slideToggle();

                // We have to refresh sliders if their are in a collapsed element (grip position issue)
                try {
                    $('.nstSlider').each(function () {
                        $(this).nstSlider('refresh');
                    });
                } catch (e) {
                }
            }
        })

        // Changing the type of the search (all / technologies / approaches)
        .on('click', '.search-type-select a', function(e) {
            e.preventDefault();

            // Set hidden value
            $('#search-type').val($(this).data('type'));

            // Set display
            $('#search-type-display').text($(this).text());
        })
        
        .on('click', '.js-expand-all-sections', function(e) {
            e.preventDefault();
            var isCollapsed = $(this).data('is-collapsed'),
                expandAll = $(this).find('.js-is-expanded'),
                collapseAll = $(this).find('.js-is-collapsed'),
                content = $($(this).data('selector'));

            if (isCollapsed) {
                // Expand all
                content.slideDown();
                expandAll.hide();
                collapseAll.show();
            } else {
                // Collapse all
                content.slideUp();
                expandAll.show();
                collapseAll.hide();
            }
            $(this).data('is-collapsed', !isCollapsed);
        })

        .on('submit', '.js-submit-once', function(e) {
            $(this).find('input[type=submit]').addClass('disabled');
        })

        .on('click', 'a.disabled', function(e) {
            e.preventDefault();
        })

        .on('click', 'input[type=submit].disabled', function(e) {
            e.preventDefault();
        })

        .on('click', '.js-sticky-entry-link-toggle', function(e) {
            e.preventDefault();
            $(this).closest('.sticky-entry').toggleClass('sticky-entry-active');
        });

    // Update the numbering of the questiongroups
    updateNumbering();
});


/**
 * detect IE
 * returns version of IE or false, if browser is not Internet Explorer
 *
 * Shamelessly copied from here: https://codepen.io/gapcode/pen/vEJNZN
 */
function detectIE() {
  var ua = window.navigator.userAgent;

  // Test values; Uncomment to check result …

  // IE 10
  // ua = 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0)';

  // IE 11
  // ua = 'Mozilla/5.0 (Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko';

  // Edge 12 (Spartan)
  // ua = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36 Edge/12.0';

  // Edge 13
  // ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2486.0 Safari/537.36 Edge/13.10586';

  var msie = ua.indexOf('MSIE ');
  if (msie > 0) {
    // IE 10 or older => return version number
    return parseInt(ua.substring(msie + 5, ua.indexOf('.', msie)), 10);
  }

  var trident = ua.indexOf('Trident/');
  if (trident > 0) {
    // IE 11 => return version number
    var rv = ua.indexOf('rv:');
    return parseInt(ua.substring(rv + 3, ua.indexOf('.', rv)), 10);
  }

  var edge = ua.indexOf('Edge/');
  if (edge > 0) {
    // Edge (IE 12+) => return version number
    return parseInt(ua.substring(edge + 5, ua.indexOf('.', edge)), 10);
  }

  // other browser
  return false;
}

var ie_version = detectIE();
if (ie_version !== false && ie_version < 12) {
    // IE: Add class to HTML element which allows overwriting certain styles.
    $('html').addClass('ie');
    
    $('.ie-warning').show();
}
