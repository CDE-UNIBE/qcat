Summary
=======

This describes the ideas and workflow of how questionnaires are exported as pdf.
As of now, there is only one type of summary which displays the questionnaire
in full - so its not actually a summary but just a pdf-export.

Following changes are planned:

* Users should be able to select/deselect sections in the pdf (description,
  location, etc.). So editing the markup before creating the PDF will be
  required.
* Changes in the output format (paper formats, fields on display) should be
  configurable.


Idea and rationale
------------------

The summary is not a fixed (hard coded) view, but its content may change
depending on configuration and version of the config.

The relevant sections for the summary of each questionnaire are defined in the
config. Gathering data for the summary happens in two steps:

* Parser: get combined data from config and questionnaire (use the same
  functionality as the questionnaire API resource)
* Renderer: filter, aggregate and annotate data specifically for the summary

The naming (parser and renderer) is not 100% precise, but indicates the idea.

The created HTML is then converted to PDF with wkhtmltopdf.

This concept was decided upon because:

* Frontend work can be sourced to external colleagues
* Robust handling of data (questionnaires and configs will change)
* More summary types can be added later
* HTML can be converted to different formats (doc) as well
* The very first step of combining data from config and questionnaire was
  required for another project as well (API)


Technical workflow
------------------

* The view ```summary.views.QuestionnaireSummaryPDFCreateView``` is called
* Data for the summary is created with the defined renderer in
  ```summary.renderers```. This renderer set up the data by the according to
  summary type and configuration.
* In the parser module (```summary.parsers```), questionnaire and configuration
  data is combined with the same class built for the questionnaire detail API
  resource: ```configuration.configured_questionnaire.ConfiguredQuestionnaire```
* The full data is then prepared as defined in the configuration.
* The initial idea was to define each question which must appear in the summary.
  This 'whitelisting' is not always a good fit due to repeating questions/
  questiongroups. Therefore, specific data preparation methods are available on
  the parsers classes.


Add a new summary type
----------------------
* Either subclass ```summary.views.SummaryPDFCreateView``` with a custom
  summary-type, or refactor the class for dynamic usage via get param or such.
* Define a renderer in ```summary.views.SummaryPDFCreateView.render_classes```
* A new template may be created (```summary.templates.layout```) and can be
  passed as GET-parameter to the view.
* Extend or create the renderer and according templates


Add a new field
---------------
* In the fixtures-json file, find the desired question and add the summay-config
  to the 'configuration' value (see examples below).
* Depending on the complexity of the question(s) involved, a specific data
  loading method on the parser may be required (but is optional).
* For most questions, the default data loading is fine - simply add the field
  on the respective renderer.
* Minimal example
  ::
    "configuration": {
      "type": "radio",
      "summary": {                     # summary config starts here
        "types": ["full"],             # list with all summary-types
          "default": {
            "field_name": "some_name"  # the key which will be used for this data in the summary
          }
        }
      }

* Full example
  ::
    "configuration": {
      "type": "radio",
      "summary": {
        "types": ["full"],
        "default": {
          "field_name": {
            "qg_31.question_keyword": "field_name_one",  # when the same question is used in multiple questiongroups:
            "qg_97.question_keyword": "field_name_two"   # provide different access-keys in the summary
          },
          "get_value": {                                 # use a custom method on the parser
            "name": "get_qg_values_with_scale",          # name of the method
            "kwargs": {
              "qg_style": "radio"                        # additional kwargs passed to the method
            }
          }
        }
      }
    }


History
-------

* It was planned to pass JSON to the frontend and do all conversion to html with
  handlebars. This was rejected from we are cube with regard to technical
  feasibility.
* wkhtmltopdf was selected based on a demo-HTML / proof of concept.
