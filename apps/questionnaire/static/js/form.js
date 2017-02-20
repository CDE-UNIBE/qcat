function addFormset(keyword) {
    /**
        Inspired by: http://stackoverflow.com/a/669982/841644
    */
    var formset_selector = '.' + keyword;
    var newElement = $(formset_selector+':last').clone(true);
    var total = $(formset_selector).length;
    var y = '#id_' + keyword + '-MAX_NUM_FORMS';
    var max = $('#id_' + keyword + '-MAX_NUM_FORMS').val();
    if (total >= max) return;
    newElement.find(':input').each(function() {
        var name = $(this).attr('name').replace('-' + (total-1) + '-','-' + total + '-');
        var id = 'id_' + name;
        $(this).attr({'name': name, 'id': id}).val('').removeAttr('checked');
    });
    newElement.find('label').each(function() {
        var newFor = $(this).attr('for').replace('-' + (total-1) + '-','-' + total + '-');
        $(this).attr('for', newFor);
    });
    total++;
    $('#id_' + keyword + '-TOTAL_FORMS').val(total);
    $(formset_selector).after(newElement);
}
