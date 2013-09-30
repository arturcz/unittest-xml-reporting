import os
import time

from unittest import result, util

from . import builder

__all__ = ('XMLTestResult',)


class XMLTestResult(result.TestResult):
    """This is a TestResult subclass that uses the unittest callbacks to create
    a XML test report similar to the ones generated by Ant for JUnit, which is
    the de facto standard and widely supported by a wide variety of tools such
    as Continuous Integration servers.
    """

    def __init__(self, stream=None, descriptions=None, verbosity=None,
            out_dir='.', out_suffix=None):
        """Creates a new instance that is capable of generating a XML test
        report file inside `out_dir`.

        The file will be named "TESTS-TestSuites-<out_suffix>.xml", where
        `out_suffix` can contain a placeholder (i.e. "my-suffix-{0}") which will
        hold the current timestamp. If `out_suffix` is ommitted, it will be the
        current timestamp.
        """
        super(XMLTestResult, self).__init__(stream, descriptions, verbosity)

        self._builder = builder.XMLContextBuilder()
        self._last_suite = None

        self.out_dir = out_dir
        self.buffer = True

        if out_suffix:
            self.out_suffix = out_suffix.format(self._timestamp())
        else:
            self.out_suffix = self._timestamp()

    def startTestRun(self):
        super(XMLTestResult, self).startTestRun()
        self._builder.begin_context('testsuites', 'TestSuites')

    def stopTestRun(self):
        super(XMLTestResult, self).stopTestRun()
        self._generate_report()

    def startTest(self, test):
        super(XMLTestResult, self).startTest(test)

        if self._builder.context_tag() == 'testsuites' or \
                self._current_suite_finished(test):
            self._start_new_suite(test)

        self._builder.begin_context('testcase', self._get_description(test))

    def stopTest(self, test):
        out_data = self._stdout_buffer.getvalue()
        err_data = self._stderr_buffer.getvalue()

        super(XMLTestResult, self).stopTest(test)

        if out_data:
            self._builder.append_cdata_section('system-out', out_data)

        if err_data:
            self._builder.append_cdata_section('system-err', err_data)

        self._builder.increment_counter('tests')
        self._builder.end_context()

    def addSkip(self, test, reason):
        super(XMLTestResult, self).addSkip(test, reason)
        self._builder.increment_counter('skipped')
        self._builder.append('skipped', None, message=reason)

    def addError(self, test, err):
        super(XMLTestResult, self).addError(test, err)
        self._builder.increment_counter('errors')
        self._append_error_data(test, 'error', err)

    def addFailure(self, test, err):
        super(XMLTestResult, self).addFailure(test, err)
        self._add_generic_failure(test, err)

    def addUnexpectedSuccess(self, test):
        super(XMLTestResult, self).addUnexpectedSuccess(test)
        self._add_generic_failure(test)

    def _add_generic_failure(self, test, err=None):
        """Accounts for a test failure.
        """
        self._builder.increment_counter('failures')
        self._append_error_data(test, 'failure', err)

    def _current_suite_finished(self, test):
        """Returns whether `test` is part of a new test suite.
        """
        return self._last_suite != self._test_class_name(test)

    def _start_new_suite(self, test):
        """Starts a new 'testsuite' section.
        """
        if self._last_suite:
            self._builder.end_context()

        self._last_suite = self._test_class_name(test)
        self._builder.begin_context('testsuite', self._last_suite)

    def _get_description(self, test):
        """Returns the first line of `test` docstring or the method name if
        no docstring is defined.
        """
        doc_first_line = test.shortDescription()
        if doc_first_line:
            return doc_first_line

        return test._testMethodName

    def _append_error_data(self, test, error_type, err=None):
        """Adds a 'failure' or 'error' element for a failed test.
        """
        cdata = None
        params = {'message': 'Unexpected success'}

        if err:
            exctype, value = err[:2]
            params['type'] = exctype.__name__
            params['message'] = str(value).splitlines()[0]
            cdata = self._exc_info_to_string(err, test)

        self._builder.append(error_type, cdata, **params)

    def _test_class_name(self, test):
        """Returns the class name formatted as "<module>.<class_name>".
        """
        return util.strclass(test.__class__)

    def _timestamp(self):
        """Returns the current timestamp.
        """
        return time.strftime("%Y%m%dT%H%M%S")

    def _generate_report(self):
        """Writes the XML document built up until now.
        """
        # Assume that self.out_dir is a stream by default
        stream = self.out_dir

        if type(stream) is str:
            filename = '{0}{1}TESTS-TestSuites-{3}.xml'.format(stream, os.sep,
                'suite', self.out_suffix)

            if not os.path.exists(stream):
                os.makedirs(stream)

            stream = open(filename, 'w')

        stream.write(self._builder.finish())
