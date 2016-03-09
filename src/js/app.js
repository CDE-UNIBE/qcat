$(document).foundation({
  equalizer : {
    equalize_on_stack: true
  },
  interchange: {
    named_queries : {
      smallretina : 'only screen and (min-width: 1px) and (-webkit-min-device-pixel-ratio: 2), only screen and (min-width: 1px) and (min--moz-device-pixel-ratio: 2), only screen and (min-width: 1px) and (-o-min-device-pixel-ratio: 2/1), only screen and (min-width: 1px) and (min-device-pixel-ratio: 2), only screen and (min-width: 1px) and (min-resolution: 192dpi), only screen and (min-width: 1px) and (min-resolution: 2dppx)',
      mediumretina : 'only screen and (min-width: 641px) and (-webkit-min-device-pixel-ratio: 2), only screen and (min-width: 641px) and (min--moz-device-pixel-ratio: 2), only screen and (min-width: 641px) and (-o-min-device-pixel-ratio: 2/1), only screen and (min-width: 641px) and (min-device-pixel-ratio: 2), only screen and (min-width: 641px) and (min-resolution: 192dpi), only screen and (min-width: 641px) and (min-resolution: 2dppx)',
      largeretina : 'only screen and (min-width: 1025px) and (-webkit-min-device-pixel-ratio: 2), only screen and (min-width: 1025px) and (min--moz-device-pixel-ratio: 2), only screen and (min-width: 1025px) and (-o-min-device-pixel-ratio: 2/1), only screen and (min-width: 1025px) and (min-device-pixel-ratio: 2), only screen and (min-width: 1025px) and (min-resolution: 192dpi), only screen and (min-width: 1025px) and (min-resolution: 2dppx)'
    }
  }
});


var sourceSwap = function () {
  var $this = $(this);
  var newSource = $this.data('alt-src');
  $this.data('alt-src', $this.attr('src'));
  $this.attr('src', newSource);
}

// Replace svg with png if no svg
if (!Modernizr.svg) {
  $('img[src$=".svg"]').each(function() {
      //E.g replaces 'logo.svg' with 'logo.png'.
      $(this).attr('src', $(this).attr('src').replace('.svg', '.png'));
  });
}


/**
 * Update the numbering of the questiongroups.
 */
function updateNumbering() {
  $('.questiongroup-numbered-inline').each(function() {
    var counter = 0;
    $(this).find('.row.list-item').each(function() {
      counter++;
      $(this).find('label').each(function() {
        var label = $(this).html();
        $(this).html(counter + ': ' + label);
      });
    });
  });
  $('.questiongroup-numbered-prefix').each(function() {
    var counter = 1;
    $(this).find('input[id$=__order]').each(function() {
      $(this).val(counter++);
    });
    counter = 1;
    $(this).find('.questiongroup-numbered-number').each(function() {
      $(this).html(counter++ + ':');
    });
  });
}


$(function() {

  // Language switcher
  $('.top-bar-lang .dropdown a').click(function(e) {
    // e.preventDefault();
    var lang = $(this).data('language');
    var form = $(this).closest('form');
    if (form && lang) {
      form.find('#language_field').val(lang);
      form.submit();
    }
  });

  $('#submit-search').click(function() {
    $(this).closest('form').submit();
    return false;
  });

  // Context switcher (WOCAT vs. Approaches vs. Technologies)
  $('.search-switch.button-switch input').click(function() {
    window.location = $(this).data('url');
  });

  $('img[data-alt-src]').each(function() {
      new Image().src = $(this).data('alt-src');
  }).hover(sourceSwap, sourceSwap);


  // UTILITIES
  // -----------------
  // Toggle view
  $('body').on('click', '[data-toggle]', function (e) {
    var target = $('#'+ $(this).data('toggle'));
    if($(this).parent().hasClass('list-gallery-item')){
      target.slideToggle();
      toggleImageCheckboxConditional(target);
    } else if($(this).parent().hasClass('button-bar')){
      var selectedValue = $(this).find('input[type="radio"]:checked').val();
      var item = $(this).closest('.list-item');
      if(selectedValue != 'none' && !item.hasClass('is-selected')) {
        target.slideToggle();
      }
      if(selectedValue === 'none' && item.hasClass('is-selected')) {
        target.slideToggle();
      }
    } else {
      e.preventDefault();
      target.slideToggle();

      // We have to refresh sliders if their are in a collapsed element (grip position issue)
      try {
        $('.nstSlider').each(function() {
          $(this).nstSlider('refresh');
        });
      } catch(e) {}
    }
  });

  // Update the numbering of the questiongroups
  updateNumbering();
});
