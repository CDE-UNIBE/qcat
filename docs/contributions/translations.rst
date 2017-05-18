Translations
============

Thanks for wanting us to help us translate the SLM database! This article covers
instructions to get you started.


Transifex
---------

The translation of the strings on the Website is done with `Transifex`_ where
you need a free account. We will then add you as translators to
`QCAT on Transifex`_.

If you do not have an account for `Transifex`_ yet, you can send us your e-mail
address and we will add you as a translator to `QCAT on Transifex`_. You will
receive an e-mail with instructions to set up your Transifex account.

If you already have an account for `Transifex`_, you can send us your username
or the e-mail address of your account and we will add you as a translator to
`QCAT on Transifex`_.


Translating on Transifex
------------------------

Transifex has a very good documentation of the translation process on their
website. Particularly helpful are the pages on
`Getting Started as a Translator`_ and `Translating with the Web Editor`_.

Please refer to their `general documentation`_ for further help.


Hints
-----

No instant updates of translations
..................................

The translations on the `QCAT website`_ are not updated instantly. The
developers need to trigger an update for the new translations to appear on the
site. Therefore if you have finished your translations, let the developers know
that they should update the website.

HTML tags in translations
.........................

Sometimes, there are HTML tags (such as ``<strong></strong>`` in the
translation. These tags need to be added exactly as they are in the translation
as well. Make sure to close the tags: after each ``<strong>``, there should be a
``</strong>``. If you are not sure whether you have closed all tags, there is a
`service to check for closing HTML tags`_.

It can occur that there are strings **inside** the HTML tags
(such as ``<div class="row">Content</div>``). These strings inside the HTML tag
(in this case ``row``) **should not be translated**.

Examples:

+---------------------------------------------------------------------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------+
| Text                                                                                                                | Translation text                                                                                                    |
+=====================================================================================================================+=====================================================================================================================+
| <strong>Type of measure</strong>: refer to 3.6                                                                      | <strong>Type de mesures</strong>: se référez à la section 3.6                                                       |
+---------------------------------------------------------------------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------+
| <div class="row">Refer to 3.6</div>                                                                                 | <div class="row">Se référez à la section 3.6</div>                                                                  |
+---------------------------------------------------------------------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------+
| <div class="row"><div class="medium-6 columns"><img src="/static/assets/img/smallmedium_QTKEN05_1.jpg"></div></div> | <div class="row"><div class="medium-6 columns"><img src="/static/assets/img/smallmedium_QTKEN05_1.jpg"></div></div> |
+---------------------------------------------------------------------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------+


Placeholders in translations
............................

Curly brackets (``{}``) serve as placeholders and should be added exactly as
they are in the translation as well. Sometimes, they contain keywords (such as
``{user}``) which **should not be translated** but added identically to the
translation.

Other placeholders are ``%(keyword)s``. Again, these need to be added exactly as
they are in the translation.

.. hint::
    In Transifex, these placeholders are highlighted in the original text in an
    orange color. You can click on these highlighted placeholders in the original
    text to copy them to the translation.

+-----------------------------------------------------+---------------------------------------------------------------+
| Text                                                | Translation text                                              |
+=====================================================+===============================================================+
| Welcome {}                                          | Bienvenue {}                                                  |
+-----------------------------------------------------+---------------------------------------------------------------+
| This questionnaire is locked for editing by {user}. | Ce questionnaire est verrouillé pour modification par {user}. |
+-----------------------------------------------------+---------------------------------------------------------------+
| View this %(questionnaire_type)s.                   | Voir cette %(questionnaire_type)s.                            |
+-----------------------------------------------------+---------------------------------------------------------------+


.. _Transifex: https://www.transifex.com/
.. _QCAT on Transifex: https://www.transifex.com/university-of-bern-cde/qcat
.. _Getting Started as a Translator: https://docs.transifex.com/getting-started/translators
.. _Translating with the Web Editor: https://docs.transifex.com/translation/translating-with-the-web-editor
.. _general documentation: https://docs.transifex.com/
.. _QCAT website: https://qcat.wocat.net
.. _service to check for closing HTML tags: https://www.aliciaramirez.com/closing-tags-checker/
