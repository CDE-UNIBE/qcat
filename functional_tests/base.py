from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from nose.plugins.attrib import attr
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from unittest import skipUnless

from accounts.authentication import WocatAuthenticationBackend
from accounts.client import Typo3Client
from qcat.tests import TEST_CACHES
from unittest.mock import patch
from accounts.tests.test_models import create_new_user

loginRouteName = 'login'


def check_firefox_path():
    """
    Check if a path for Firefox to be used by Selenium is specified in
    the (local) settings.

    Returns:
        ``bool``. Returns ``True`` if the setting
        ``TESTING_FIREFOX_PATH`` is set. Returns ``False`` if the
        setting is not present or empty.
    """
    try:
        if settings.TESTING_FIREFOX_PATH != '':
            return True
    except:
        pass
    return False


@skipUnless(check_firefox_path(), "Firefox path not specified")
@override_settings(DEBUG=True)
@override_settings(CACHES=TEST_CACHES)
@attr('functional')
class FunctionalTest(StaticLiveServerTestCase):

    def setUp(self):
        self.browser = webdriver.Firefox(
            firefox_binary=FirefoxBinary(settings.TESTING_FIREFOX_PATH))
        self.browser.implicitly_wait(3)

    def tearDown(self):
        self.browser.quit()

    def findByNot(self, by, el):
        try:
            self.browser.implicitly_wait(0)
            if by == 'class_name':
                self.browser.find_element_by_class_name(el)
            elif by == 'link_text':
                self.browser.find_element_by_link_text(el)
            elif by == 'name':
                self.browser.find_element_by_name(el)
            elif by == 'xpath':
                self.browser.find_element_by_xpath(el)
            elif by == 'id':
                self.browser.find_element_by_id(el)
            else:
                self.fail('Argument "by" = "%s" is not valid.' % by)
            self.fail('Element %s was found when it should not be' % el)
        except NoSuchElementException:
            pass

    def findBy(self, by, el, base=None):
        if base is None:
            base = self.browser
        f = None
        try:
            if by == 'class_name':
                f = base.find_element_by_class_name(el)
            elif by == 'link_text':
                f = base.find_element_by_link_text(el)
            elif by == 'name':
                f = base.find_element_by_name(el)
            elif by == 'xpath':
                f = base.find_element_by_xpath(el)
            elif by == 'id':
                f = base.find_element_by_id(el)
            else:
                self.fail('Argument "by" = "%s" is not valid.' % by)
        except NoSuchElementException:
            self.fail('Element %s was not found by %s' % (el, by))
        return f

    def findManyBy(self, by, el, base=None):
        if base is None:
            base = self.browser
        f = None
        try:
            if by == 'class_name':
                f = base.find_elements_by_class_name(el)
            elif by == 'link_text':
                f = base.find_elements_by_link_text(el)
            elif by == 'name':
                f = base.find_elements_by_name(el)
            elif by == 'xpath':
                f = base.find_elements_by_xpath(el)
            elif by == 'id':
                f = base.find_elements_by_id(el)
            else:
                self.fail('Argument "by" = "%s" is not valid.' % by)
        except NoSuchElementException:
            self.fail('Elements %s were not found by %s' % (el, by))
        return f

    def changeHiddenInput(self, el, val):
        self.browser.execute_script('''
            var elem = arguments[0];
            var value = arguments[1];
            elem.value = value;
        ''', el, val)

    def checkOnPage(self, text):
        self.assertIn(text, self.browser.page_source)

    def changeLanguage(self, locale):
        self.findBy('xpath', '//a[@data-language="{}"]'.format(locale)).click()

    @patch.object(Typo3Client, 'get_and_update_django_user')
    @patch.object(WocatAuthenticationBackend, 'authenticate')
    def doLogin(self, mock_authenticate, mock_get_and_update_django_user,
                user=None):
        self.doLogout()
        if user is None:
            user = create_new_user()
        mock_authenticate.return_value = user
        mock_authenticate.__name__ = ''
        mock_get_and_update_django_user.return_value = user
        with patch('accounts.client.typo3_client.get_user_id') as get_user_id:
            get_user_id.return_value = user.id
            self.browser.get(self.live_server_url + '/404_no_such_url/')
            self.browser.add_cookie({'name': 'fe_typo_user', 'value': 'foo'})
            self.browser.get(self.live_server_url + reverse(loginRouteName))

    def doLogout(self):
        self.browser.delete_cookie('fe_typo_user')
        self.browser.get(self.live_server_url + '/404_no_such_url/')

    def dropImage(self, dropzone_id):
        self.browser.execute_script(
            "function base64toBlob(b64Data, contentType, sliceSize) "
            "{contentType = contentType || '';sliceSize = sliceSize || 512;"
            "var byteCharacters = atob(b64Data);var byteArrays = [];for (var "
            "offset = 0; offset < byteCharacters.length; offset += sliceSize) "
            "{var slice = byteCharacters.slice(offset, offset + sliceSize);"
            "var byteNumbers = new Array(slice.length);for (var i = 0; i < "
            "slice.length; i++) {byteNumbers[i] = slice.charCodeAt(i);}var "
            "byteArray = new Uint8Array(byteNumbers);byteArrays.push("
            "byteArray);}var blob = new Blob(byteArrays, {type: "
            "contentType});return blob;}var base64Image = "
            "'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"
            "pCZbEhAAOw==';var dz = Dropzone.forElement('#%s'); dz.addFile("
            "base64toBlob(base64Image, 'image/gif'));" % dropzone_id)
