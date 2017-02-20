from django_nose import NoseTestSuiteRunner


class QcatTestSuiteRunner(NoseTestSuiteRunner):

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '-pop',
            action='store_true',
            default=False,
            help='Display browser for functional tests'
        )
