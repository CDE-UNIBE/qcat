import json
from datetime import datetime

from qcat.tests import TestCase
from wocat.management.commands.import_wocat_data import QTImport, WOCATImport, \
    ImportObject


class TestImport(WOCATImport):
    mapping = {
        'qg_1': {
            'questions': {
                'question_1_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_1_1',
                            'wocat_column': 'column_1_1',
                        }
                    ],
                    'type': 'string',
                }
            }
        },
        'qg_2': {
            'questions': {
                'question_2_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_2_1',
                            'wocat_column': 'column_2_1',
                        }
                    ],
                    'type': 'string',
                },
                'question_2_2': {
                    'mapping': [
                        {
                            'wocat_table': 'table_2_1',
                            'wocat_column': 'column_2_2',
                        }
                    ],
                    'type': 'string',
                },
            }
        },
        'qg_3': {
            'questions': {
                'question_3_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_3_1',
                            'wocat_column': 'column_3_1',
                        }
                    ],
                    'type': 'dropdown',
                    'value_mapping_list': {
                        'wocat_value_3_1': 'qcat_value_3_1',
                        'wocat_value_3_2': 'qcat_value_3_2',
                    }
                }
            }
        },
        'qg_4': {
            'questions': {
                'question_4_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_4_1',
                            'wocat_column': 'column_4_1',
                            'mapping_prefix': 'prefix_'
                        }
                    ],
                    'type': 'dropdown',
                    'value_mapping_list': {
                        'prefix_wocat_value_4_1': 'qcat_value_4_1',
                        'prefix_wocat_value_4_2': 'qcat_value_4_2',
                    }
                }
            }
        },
        'qg_5': {
            'questions': {
                'question_5_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_5_1',
                            'wocat_column': 'column_5_1',
                        }
                    ],
                    'type': 'date'
                }
            }
        },
        'qg_6': {
            'questions': {
                'question_6_1': {
                    'type': 'constant',
                    'value': 1,
                }
            }
        },
        'qg_7': {
            'questions': {
                'question_7_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_7_1',
                            'wocat_column': 'column_7_1',
                            'mapping_prefix': 'First question: '
                        },
                        {
                            'wocat_table': 'table_7_1',
                            'wocat_column': 'column_7_2',
                            'mapping_prefix': 'Second question: '
                        },
                    ],
                    'type': 'string',
                    'composite': {
                        'type': 'merge'
                    }
                }
            }
        },
        'qg_8': {
            'questions': {
                'question_8_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_8_1',
                            'wocat_column': 'column_8_1',
                        },
                        {
                            'wocat_table': 'table_8_1',
                            'wocat_column': 'column_8_2',
                        }
                    ],
                    'type': 'dropdown',
                    'composite': {
                        'type': 'geom_point'
                    }
                }
            }
        },
        'qg_9': {
            'questions': {
                'question_9_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_9_1',
                            'wocat_column': 'column_9_1',
                        },
                        {
                            'wocat_table': 'table_9_1',
                            'wocat_column': 'column_9_2',
                        },
                        {
                            'wocat_table': 'table_9_1',
                            'wocat_column': 'column_9_3',
                        }
                    ],
                    'type': 'checkbox',
                    'composite': {
                        'type': 'checkbox'
                    }
                }
            }
        },
        'qg_10': {
            'questions': {
                'question_10_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_10_1',
                            'wocat_column': 'column_10_1',
                        },
                        {
                            'wocat_table': 'table_10_1',
                            'wocat_column': 'column_9_2',
                        },
                        {
                            'wocat_table': 'table_10_1',
                            'wocat_column': 'column_10_3',
                        }
                    ],
                    'type': 'checkbox',
                    'composite': {
                        'type': 'checkbox',
                        'mapping': 'exclusive'
                    },
                    'value_mapping_list': {
                        'wocat_value_10_1': 'qcat_value_10_1',
                        'wocat_value_10_2': 'qcat_value_10_2',
                        'wocat_value_10_3': 'qcat_value_10_3',
                    }
                }
            }
        },
        'qg_11': {
            'questions': {
                'question_11_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_11_1',
                            'wocat_column': 'column_11_1',
                        },
                    ],
                    'type': 'dropdown',
                }
            },
            'conditions': [
                {
                    'mapping': [
                        {
                            'wocat_table': 'table_11_1',
                            'wocat_column': 'column_11_2'
                        },
                        {
                            'wocat_table': 'table_11_1',
                            'wocat_column': 'column_11_3'
                        }
                    ],
                    'operator': 'contains',
                    'value': 'value_11_true',
                }
            ]
        },
        'qg_12': {
            'questions': {
                'question_12_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_12_1',
                            'wocat_column': 'column_12_1',
                            'mapping_prefix': 'Value 1: ',
                            'conditions': [
                                {
                                    'mapping': [
                                        {
                                            'wocat_table': 'table_12_1',
                                            'wocat_column': 'column_12_condition_1',
                                        },
                                        {
                                            'wocat_table': 'table_12_1',
                                            'wocat_column': 'column_12_condition_2',
                                        }
                                    ],
                                    'operator': 'contains_not',
                                    'value': 'false',
                                }
                            ],
                            'condition_message': 'Condition X was true.'
                        },
                        {
                            'wocat_table': 'table_12_1',
                            'wocat_column': 'column_12_2',
                            'mapping_prefix': 'Value 2: '
                        }
                    ],
                    'type': 'string',
                    'composite': {
                        'type': 'merge'
                    }
                }
            }
        },
        'qg_13': {
            'questions': {
                'question_13_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_13_1',
                            'wocat_column': 'column_13_1',
                            'mapping_prefix': 'Value 1: ',
                            'conditions': [
                                {
                                    'mapping': [
                                        {
                                            'wocat_table': 'table_13_1',
                                            'wocat_column': 'column_13_condition_1'
                                        },
                                    ],
                                    'operator': 'contains',
                                    'value': 'true'
                                },
                                {
                                    'mapping': [
                                        {
                                            'wocat_table': 'table_13_1',
                                            'wocat_column': 'column_13_condition_2'
                                        },
                                    ],
                                    'operator': 'contains',
                                    'value': 'true'
                                },
                            ],
                            'condition_message': 'Only one needs to be true!',
                        },
                        {
                            'wocat_table': 'table_13_1',
                            'wocat_column': 'column_13_2',
                            'mapping_prefix': 'Value 2: ',
                            'conditions': [
                                {
                                    'mapping': [
                                        {
                                            'wocat_table': 'table_13_1',
                                            'wocat_column': 'column_13_condition_1'
                                        },
                                    ],
                                    'operator': 'contains',
                                    'value': 'true'
                                },
                                {
                                    'mapping': [
                                        {
                                            'wocat_table': 'table_13_1',
                                            'wocat_column': 'column_13_condition_2'
                                        },
                                    ],
                                    'operator': 'contains',
                                    'value': 'true'
                                },
                            ],
                            'condition_message': 'Both need to be true!',
                            'conditions_join': 'and'
                        }
                    ],
                    'type': 'string',
                    'composite': {
                        'type': 'merge'
                    }
                }
            }
        },
        'qg_14': {
            'questions': {
                'question_14_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_14_1',
                            'wocat_column': 'column_14_1',
                            'mapping_prefix': 'Value 1: ',
                            'conditions': [
                                {
                                    'mapping': [
                                        {
                                            'wocat_table': 'table_14_1',
                                            'wocat_column': 'column_14_condition_1',
                                        }
                                    ],
                                    'operator': 'is_empty',
                                }
                            ],
                            'condition_message': 'Condition X was true.'
                        },
                        {
                            'wocat_table': 'table_14_1',
                            'wocat_column': 'column_14_2',
                            'mapping_prefix': 'Value 2: '
                        }
                    ],
                    'type': 'string',
                    'composite': {
                        'type': 'merge'
                    }
                }
            }
        },
        'qg_15': {
            'questions': {
                'question_15_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_15_1',
                            'wocat_column': 'column_15_1',
                            'mapping_prefix': 'Value 1: ',
                        }
                    ],
                    'type': 'string',
                    'composite': {
                        'type': 'merge'
                    }
                },
                'question_15_2': {
                    'mapping': [
                        {
                            'wocat_table': 'table_15_1',
                            'wocat_column': 'column_15_1',
                            'mapping_prefix': 'Value 2: '
                        },
                        {
                            'mapping': [
                                {
                                    'wocat_table': 'table_15_1',
                                    'wocat_column': 'column_15_2',
                                },
                                {
                                    'wocat_table': 'table_15_1',
                                    'wocat_column': 'column_15_3',
                                }
                            ],
                            'type': 'string',
                            'composite': {
                                'type': 'merge',
                                'separator': ': '
                            }
                        }
                    ],
                    'type': 'string',
                    'composite': {
                        'type': 'merge'
                    }
                }
            }
        },
        'qg_16': {
            'questions': {
                'question_16_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_16_1',
                            'wocat_column': 'column_16_1',
                            'lookup_table': True
                        }
                    ],
                    'type': 'string',
                },
                'question_16_2': {
                    'mapping': [
                        {
                            'wocat_table': 'table_16_1',
                            'wocat_column': 'column_16_2',
                            'lookup_table': True
                        },
                        {
                            'wocat_table': 'table_16_1',
                            'wocat_column': 'column_16_3',
                            'lookup_table': True
                        }
                    ],
                    'type': 'string',
                    'composite': {
                        'type': 'merge',
                    }
                }
            }
        },
        'qg_17': {
            'questions': {
                'question_17_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_17_1',
                            'wocat_column': 'column_17_1',
                        },
                        {
                            'wocat_table': 'table_17_1',
                            'wocat_column': 'column_17_2',
                        },
                        {
                            'wocat_table': 'table_17_1',
                            'wocat_column': 'column_17_3',
                        }
                    ],
                    'type': 'checkbox',
                    'composite': {
                        'type': 'checkbox',
                    },
                    'value_mapping_list': {
                        'wocat_value_17_1': 'qcat_value_17_1',
                        'wocat_value_17_2': 'qcat_value_17_2',
                        'wocat_value_17_3': 'qcat_value_17_3',
                    }
                }
            }
        },
        'qg_18': {
            'questions': {
                'question_18_1': {
                    'mapping': [
                        {
                            'mapping': [
                                {
                                    'wocat_table': 'table_18_1',
                                    'wocat_column': 'column_18_1',
                                },
                                {
                                    'wocat_table': 'table_18_1',
                                    'wocat_column': 'column_18_2',
                                }
                            ],
                            'type': 'string',
                            'composite': {
                                'type': 'merge',
                                'separator': ': '
                            },
                            'conditions': [
                                {
                                    'mapping': [
                                        {
                                            'wocat_table': 'table_18_1',
                                            'wocat_column': 'column_18_condition'
                                        }
                                    ],
                                    'operator': 'contains_not',
                                    'value': 'false'
                                }
                            ],
                            'condition_message': 'Question 18_1 shown'
                        }
                    ],
                    'value_prefix': 'Prefix: ',
                    'type': 'string',
                    'composite': {
                        'type': 'merge',
                    },
                }
            }
        },
        'qg_19': {
            'questions': {
                'question_19_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_19_1',
                            'wocat_column': 'column_19_1',
                        },
                        {
                            'wocat_table': 'table_19_1',
                            'wocat_column': 'column_19_2',
                        }
                    ],
                    'type': 'dropdown',
                    'conditions': [
                        {
                            'mapping': [
                                {
                                    'wocat_table': 'table_19_1',
                                    'wocat_column': 'column_19_1',
                                },
                                {
                                    'wocat_table': 'table_19_1',
                                    'wocat_column': 'column_19_2',
                                }
                            ],
                            'operator': 'len_lte',
                            'value': 1,
                        }
                    ],
                    'condition_message': 'Question 19_1 shown'
                }
            }
        },
        'qg_20': {
            'questions': {
                'question_20_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_20_1',
                            'wocat_column': 'column_20_1',
                        }
                    ],
                    'type': 'checkbox',
                    'composite': {
                        'type': 'checkbox'
                    }
                }
            }
        },
        'qg_21': {
            'questions': {
                'question_21_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_21_1',
                            'wocat_column': 'column_21_1',
                            'value_mapping': 'Value 1',
                            'conditions': [
                                {
                                    'mapping': [
                                        {
                                            'wocat_table': 'table_21_1',
                                            'wocat_column': 'column_21_1',
                                        }
                                    ],
                                    'operator': 'contains',
                                    'value': 'foo'
                                }
                            ]
                        },
                        {
                            'wocat_table': 'table_21_1',
                            'wocat_column': 'column_21_2',
                            'value_mapping': 'Value 2',
                            'conditions': [
                                {
                                    'mapping': [
                                        {
                                            'wocat_table': 'table_21_1',
                                            'wocat_column': 'column_21_2',
                                        }
                                    ],
                                    'operator': 'contains',
                                    'value': 'foo'
                                }
                            ]
                        },
                        {
                            'wocat_table': 'table_21_1',
                            'wocat_column': 'column_21_3',
                            'value_mapping': 'Value 3',
                            'conditions': [
                                {
                                    'mapping': [
                                        {
                                            'wocat_table': 'table_21_1',
                                            'wocat_column': 'column_21_3',
                                        }
                                    ],
                                    'operator': 'contains',
                                    'value': 'foo'
                                }
                            ]
                        }
                    ],
                    'type': 'string',
                    'composite': {
                        'type': 'merge'
                    }
                }
            }
        },
        'qg_22': {
            'questions': {
                'question_22_1': {
                    'mapping': [
                        {
                            # Using a table where the value for sure only appears once!
                            'wocat_table': 'table_1_1',
                            'wocat_column': 'column_1_1',
                            'value_mapping': 'True',
                            'conditions': [
                                {
                                    'mapping': [
                                        {
                                            'wocat_table': 'table_22_1',
                                        },
                                    ],
                                    'operator': 'custom',
                                    'custom': [
                                        {
                                            'key': 'column_22_condition_1',
                                            'value': ['val_1'],
                                            'operator': 'one_of',
                                        },
                                        {
                                            'key': 'column_22_condition_2',
                                            'value': ['true'],
                                            'operator': 'one_of',
                                        }
                                    ]
                                },
                            ]
                        }
                    ],
                    'type': 'string'
                }
            }
        },
        'qg_23': {
            'questions': {
                'question_23_1': {
                    'mapping': [
                        {
                            'wocat_column': 'column_23_1'
                        }
                    ],
                    'type': 'string',
                },
                'question_23_2': {
                    'mapping': [
                        {
                            'wocat_column': 'column_23_2'
                        }
                    ],
                    'type': 'string',
                }
            },
            'repeating': True,
            'wocat_table': 'table_23_1'
        },
        'qg_24': {
            'questions': {
                'question_24_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_24_1',
                            'wocat_column': 'column_24_1',
                            'index_filter': [
                                {
                                    'mapping': [
                                        {
                                            'wocat_table': 'table_24_1',
                                            'wocat_column': 'column_24_condition'
                                        }
                                    ],
                                    'operator': 'equals',
                                    'value': '1',
                                }
                            ]
                        }
                    ],
                    'type': 'string'
                }
            }
        },
        'qg_25': {
            'questions': {
                'question_25_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_25_1',
                            'wocat_column': 'column_25_1_1',
                            'order_value': 'b',
                        },
                        {
                            'wocat_table': 'table_25_2',
                            'wocat_column': 'column_25_2_1',
                            'order_value': 'a',
                        }
                    ],
                    'type': 'string',
                },
                'question_25_2': {
                    'mapping': [
                        {
                            'wocat_table': 'table_25_1',
                            'wocat_column': 'column_25_1_2',
                            'order_value': 'b',
                        },
                        {
                            'wocat_table': 'table_25_2',
                            'wocat_column': 'column_25_2_2',
                            'order_value': 'a',
                        }
                    ],
                    'type': 'string',
                },
                'question_25_3': {
                    'mapping': [
                        {
                            'wocat_table': 'table_25_1',
                            'wocat_column': 'column_25_1_3',
                            'order_value': 'b',
                        },
                        {
                            'wocat_table': 'table_25_2',
                            'wocat_column': 'column_25_2_3',
                            'order_value': 'a',
                        },
                    ],
                    'type': 'dropdown'
                },
                'question_25_4': {
                    'mapping': [
                        {
                            'wocat_table': 'table_25_1',
                            # 'wocat_column': 'column_25_1_4',  # Not necessary
                            'order_value': 'b',
                            'value_mapping': 'value_1'
                        },
                        {
                            'wocat_table': 'table_25_2',
                            # 'wocat_column': 'column_25_2_4',
                            'order_value': 'a',
                            'value_mapping': 'value_2'
                        }
                    ],
                    'type': 'dropdown'
                }
            },
            'repeating_rows': True,
            'unique': True,
            'mapping_order_column': {
                'wocat_table': 'table_25_3',
                'wocat_column': 'column_25_3_1'
            },
            'sort_function': 'sort_by_key(k, "sort_order")',
        },
        'qg_26': {
            'questions': {
                # other: rank
                'question_26_1': {
                    'mapping': [
                        {
                            'wocat_table': 'table_26_1',
                            'wocat_column': 'column_26_1_1'
                        },
                        {
                            'wocat_table': 'table_26_1',
                            'wocat_column': 'column_26_1_3'
                        },
                    ],
                    'type': 'dropdown',
                },
                # other: specify
                'question_26_2': {
                    'mapping': [
                        {
                            'wocat_table': 'table_26_1',
                            'wocat_column': 'column_26_1_2'
                        },
                        {
                            'wocat_table': 'table_26_1',
                            'wocat_column': 'column_26_1_4'
                        },
                    ],
                    'type': 'string',
                }
            },
            'to_repeating_questiongroup': True,
        },
        'qg_27': {
            'questions': {
                'question_27_1': {
                    'mapping': [
                        {
                            'mapping': [
                                {
                                    'wocat_table': 'table_27_1',
                                    'wocat_column': 'column_27_1_1'
                                },
                                {
                                    'wocat_table': 'table_27_1',
                                    'wocat_column': 'column_27_1_2',
                                    'mapping_prefix': 'Other: '
                                }
                            ]
                        },
                        {
                            'mapping': [
                                {
                                    'wocat_table': 'table_27_1',
                                    'wocat_column': 'column_27_1_3'
                                },
                                {
                                    'wocat_table': 'table_27_1',
                                    'wocat_column': 'column_27_1_4',
                                    'mapping_prefix': 'Other: '
                                }
                            ]
                        }
                    ],
                    'type': 'string',
                },
            },
            'split_questions': True,
        },
        'qg_28': {
            'questions': {
                'question_28_1': {
                    'mapping': [
                        {
                            'mapping': [
                                {
                                    'wocat_table': 'table_28_1',
                                    'wocat_column': 'column_28_1_1'
                                }
                            ]
                        },
                        {
                            'mapping': [
                                {
                                    'wocat_table': 'table_28_1',
                                    'wocat_column': 'column_28_1_2'
                                }
                            ]
                        },
                        {
                            'mapping': [
                                {
                                    'wocat_table': 'table_28_1',
                                    'wocat_column': 'column_28_1_3'
                                }
                            ]
                        }
                    ],
                    'type': 'string',
                }
            },
            'split_questions': True,
        }
    }
    configuration_code = 'sample'


"""
index_filter

Use case:
    qt_id   measure_type     vegetative
    1       type_1           veg_1
    1       type_1           veg_2
    1       type_2           veg_3

We would like to collect all "vegetative" values where "measure_type" = "type_1".
Conditions would not work because if it evaluates to TRUE, it would also contain
"veg_3". Use index_filter instead.

See qg_24 for example.
"""


class DoMappingTest(TestCase):

    fixtures = [
        'groups_permissions',
        'sample_user',
    ]

    def setUp(self):

        self.imprt = TestImport({'verbosity': 2})

        lookup_table = {
            1: {
                'english': 'English 1',  # en
                'french': 'French 1',  # fr
                'spanish': 'Spanish 1'  # es
            },
            2: {
                'english': 'English 2',  # en
                'french': 'French 2',  # fr
                'spanish': 'Spanish 2'  # es
            },
            3: {
                'english': 'English 3',  # en
                'french': 'French 3',  # fr
                'spanish': 'Spanish 3'  # es
            }
        }
        lookup_table_text = {}
        file_infos = {}
        image_url = ''

        import_object_1 = ImportObject(
            identifier=1, command_options={}, lookup_table=lookup_table,
            lookup_table_text=lookup_table_text, file_infos=file_infos,
            image_url=image_url)
        import_object_1.code = 'code_1'
        import_object_1.wocat_data = {
            'table_1_1': [
                {
                    'column_1_1': 'Foo'
                }
            ],
            'table_2_1': [
                {
                    'column_2_1': 'Foo',
                    'column_2_2': 'Bar',
                }
            ],
            'table_3_1': [
                {
                    'column_3_1': 'wocat_value_3_1'
                }
            ],
            'table_4_1': [
                {
                    'column_4_1': 'wocat_value_4_1'
                }
            ],
            'table_5_1': [
                {
                    'column_5_1': '2010-04-20'
                }
            ],
            'table_7_1': [
                {
                    'column_7_1': 'Foo',
                    'column_7_2': 'Bar'
                }
            ],
            'table_8_1': [
                {
                    'column_8_1': '46.0',
                    'column_8_2': '5.0'
                }
            ],
            'table_9_1': [
                {
                    'column_9_1': 'value_9_1',
                    'column_9_3': 'value_9_3'
                }
            ],
            'table_10_1': [
                {
                    'column_10_1': 'wocat_value_10_1',
                    'column_10_3': 'wocat_value_10_3',
                }
            ],
            'table_11_1': [
                {
                    'column_11_1': 'value_11_1',
                    'column_11_3': 'value_11_true'
                }
            ],
            'table_12_1': [
                {
                    'column_12_1': 'Foo',
                    'column_12_2': 'Bar',
                    'column_12_condition_1': 'true',
                    'column_12_condition_2': 'foo',
                }
            ],
            'table_13_1': [
                {
                    'column_13_1': 'Foo',
                    'column_13_2': 'Bar',
                    'column_13_condition_1': 'true',
                    'column_13_condition_2': 'true',
                }
            ],
            'table_14_1': [
                {
                    'column_14_1': 'Foo',
                    'column_14_2': 'Bar',
                    'column_14_condition_1': '',
                }
            ],
            'table_15_1': [
                {
                    'column_15_1': 'Foo',
                    'column_15_2': 'Bar',
                    'column_15_3': 'Faz',
                }
            ],
            'table_16_1': [
                {
                    'column_16_1': 1,
                    'column_16_2': 2,
                    'column_16_3': 3,
                }
            ],
            'table_17_1': [
                {
                    'column_17_1': 'wocat_value_17_1',
                    'column_17_2': 'wocat_value_17_5',
                }
            ],
            'table_18_1': [
                {
                    'column_18_1': 'Value 18_1',
                    'column_18_2': 'Value 18_2',
                    'column_18_condition': 'true',
                }
            ],
            'table_19_1': [
                {
                    'column_19_1': 'true',
                }
            ],
            'table_20_1': [
                {
                    'column_20_1': 'foo',
                }
            ],
            'table_21_1': [
                {
                    'column_21_1': 'foo',
                    'column_21_2': 'bar',
                    'column_21_3': 'foo',
                }
            ],
            'table_22_1': [
                {
                    'column_22_1': 'Foo',
                    'column_22_condition_1': 'val_1',
                    'column_22_condition_2': 'true',
                },
                {
                    'column_22_1': 'Bar',
                    'column_22_condition_1': 'val_2',
                    'column_22_condition_2': 'true',
                },
                {
                    'column_22_1': 'Faz',
                    'column_22_condition_1': 'val_1',
                    'column_22_condition_2': 'false',
                },
            ],
            'table_23_1': [
                {
                    'column_23_1': 'Foo 1',
                    'column_23_2': 'Faz 1',
                },
                {
                    'column_23_1': 'Foo 2',
                    'column_23_2': 'Faz 2',
                }
            ],
            'table_24_1': [
                {
                    'column_24_1': 'Foo',
                    'column_24_condition': '1'
                },
                {
                    'column_24_1': 'Bar',
                    'column_24_condition': '2'
                },
                {
                    'column_24_1': 'Faz',
                    'column_24_condition': '2'
                }
            ],
            'table_25_1': [
                {
                    'column_25_1_1': 'Foo 1',
                    'column_25_1_2': 'Faz 1',
                    'column_25_1_3': '1',
                    'sort_order': '2'
                },
                {
                    'column_25_1_1': 'Foo 2',
                    'column_25_1_2': 'Faz 2',
                    'column_25_1_3': '2',
                    'sort_order': '1',
                }
            ],
            'table_25_2': [
                {
                    'column_25_2_1': 'Foo 3',
                    'column_25_2_2': 'Faz 3',
                    'column_25_2_3': '3',
                },
                {
                    'column_25_2_1': 'Foo 4',
                    'column_25_2_2': 'Faz 4',
                    'column_25_2_3': '4',
                },
                {
                    # Will be removed
                    'column_25_2_1': '',
                    'column_25_2_2': '',
                    'column_25_2_3': '',
                }
            ],
            'table_25_3': [
                {
                    'column_25_3_1': 'ab'
                }
            ],
            'table_26_1': [
                {
                    'column_26_1_1': '1',
                    'column_26_1_2': 'Foo',
                    'column_26_1_3': '2',
                    'column_26_1_4': 'Bar',
                }
            ],
            'table_27_1': [
                {
                    'column_27_1_1': 'one one',
                    'column_27_1_2': 'one two',
                    'column_27_1_3': 'two one',
                    'column_27_1_4': 'two two',
                }
            ],
            'table_28_1': [
                {
                    'column_28_1_1': 'one',
                    'column_28_1_2': 'two',
                }
            ]
        }
        lookup_table_text = {}
        file_infos = {}
        image_url = ''

        import_object_2 = ImportObject(
            identifier=2, command_options={}, lookup_table=lookup_table,
            lookup_table_text=lookup_table_text, file_infos=file_infos,
            image_url=image_url)

        import_object_2.code = 'code_2'
        import_object_2.wocat_data = {
            'table_1_1': [
                {
                    'column_1_2': 'Foo'
                }
            ],
            'table_2_1': [
                {
                    'column_2_1': 'Faz',
                }
            ],
            'table_3_1': [
                {
                    'column_3_1': 'wocat_value_not_mapped'
                }
            ],
            'table_4_1': [
                {
                    'column_4_1': 'wocat_value_not_mapped'
                }
            ],
            'table_5_1': [
                {
                    'column_5_1': '2000-01-01'
                }
            ],
            'table_7_1': [
                {
                    'column_7_2': 'Faz',
                }
            ],
            'table_8_1': [
                {
                    'column_8_1': '38°35\'52.48"N',
                    'column_8_2': '38°35\'52.48"N'
                }
            ],
            'table_9_1': [
                {
                    'column_9_2': 'value_9_2',
                },
                {
                    'column_9_3': 'value_9_2',
                }
            ],
            'table_10_1': [
                {
                    'column_10_1': 'wocat_value_10_2',
                    'column_10_3': 'not_mapped_value'
                }
            ],
            'table_11_1': [
                {
                    'column_11_1': 'value_11_1',
                    'column_11_3': 'value_11_false'
                }
            ],
            'table_12_1': [
                {
                    'column_12_1': 'Faz',
                    'column_12_2': 'Taz',
                    'column_12_condition_1': 'false',
                    'column_12_condition_2': 'foo',
                }
            ],
            'table_13_1': [
                {
                    'column_13_1': 'Foo',
                    'column_13_2': 'Bar',
                    'column_13_condition_1': 'true',
                    'column_13_condition_2': 'false',
                }
            ],
            'table_14_1': [
                {
                    'column_14_1': 'Foo',
                    'column_14_2': 'Bar',
                    'column_14_condition_1': 'true',
                }
            ],
            'table_15_1': [
                {
                    'column_15_1': 'Foo',
                    'column_15_3': 'Faz',
                }
            ],
            'table_16_1': [
                {
                    'column_16_1': 4,
                    'column_16_2': 5,
                    'column_16_3': 6,
                }
            ],
            'table_17_1': [
                {
                    'column_17_1': 'wocat_value_17_0',
                    'column_17_2': 'wocat_value_17_2',
                }
            ],
            'table_18_1': [
                {
                    'column_18_1': 'Value 18_1',
                    'column_18_2': 'Value 18_2',
                    'column_18_condition': 'false',
                }
            ],
            'table_19_1': [
                {
                    'column_19_1': 'true',
                    'column_19_2': 'true',
                }
            ],
            'table_20_1': [
                {
                    'column_20_1': 'foo',
                },
                {
                    'column_20_1': 'bar',
                }
            ],
            'table_21_1': [
                {
                    'column_21_1': 'foo',
                    'column_21_2': 'foo',
                    'column_21_3': 'bar',
                }
            ],
            'table_22_1': [
                {
                    'column_22_1': 'Foo',
                    'column_22_condition_1': 'val_1',
                    'column_22_condition_2': 'false',
                },
                {
                    'column_22_1': 'Bar',
                    'column_22_condition_1': 'val_2',
                    'column_22_condition_2': 'true',
                },
            ],
            'table_24_1': [
                {
                    'column_24_1': 'Foo',
                    'column_24_condition': '2'
                },
                {
                    'column_24_1': 'Bar',
                    'column_24_condition': '1'
                },
                {
                    'column_24_1': 'Faz',
                    'column_24_condition': '1'
                }
            ],
            'table_25_1': [
                {
                    'id': 1,
                    'column_25_1_1': 'Foo 1',
                    'column_25_1_2': 'Faz 1',
                },
                {
                    'id': 2,
                    'column_25_1_1': 'Foo 2',
                },
                {
                    # Duplicate entry, will be removed.
                    'id': 3,
                    'column_25_1_1': 'Foo 1',
                    'column_25_1_2': 'Faz 1',
                },
            ],
            'table_25_2': [
                {
                    'id': 1,
                    'column_25_2_2': 'Faz 3',
                },
                {
                    'id': 2,
                    'column_25_2_1': 'Foo 4',
                    'column_25_2_2': 'Faz 4',
                }
            ],
        }
        lookup_table_text = {}
        file_infos = {}
        image_url = ''

        # Original
        import_object_3 = ImportObject(
            identifier=3, command_options={}, lookup_table=lookup_table,
            lookup_table_text=lookup_table_text, file_infos=file_infos,
            image_url=image_url)

        import_object_3.set_code('T_MOR010en')
        import_object_3.created = datetime.now()
        import_object_3.wocat_data = {
            'table_1_1': [
                {
                    'column_1_1': 'English'
                }
            ],
            'table_3_1': [
                {
                    'column_3_1': 'wocat_value_3_1'
                }
            ],
            'table_24_1': [
                {
                    'column_24_1': 'Foo',
                    'column_24_condition': '2'
                },
                {
                    'column_24_1': 'Bar',
                    'column_24_condition': '2'
                },
                {
                    'column_24_1': 'Faz',
                    'column_24_condition': '2'
                }
            ],
            'table_25_1': [
                {
                    'column_25_1_1': 'Foo 1 English',
                    'column_25_1_2': 'Faz 1 English',
                },
                {
                    'column_25_1_1': 'Foo 2 English',
                    'column_25_1_2': 'Faz 2 English',
                }
            ],
            'table_25_2': [
                {
                    'column_25_2_1': 'Foo 3 English',
                    'column_25_2_2': 'Faz 3 English',
                },
                {
                    'column_25_2_1': 'Foo 4 English',
                    'column_25_2_2': 'Faz 4 English',
                }
            ],
            'table_27_1': [
                {
                    'column_27_1_1': 'one one',
                    'column_27_1_2': 'one two',
                    'column_27_1_3': 'two one',
                    'column_27_1_4': 'two two',
                }
            ],
            'table_28_1': [
                {
                    'column_28_1_1': 'one',
                    'column_28_1_2': 'two',
                }
            ]
        }
        lookup_table_text = {}
        file_infos = {}
        image_url = ''

        # Translation of 3
        import_object_4 = ImportObject(
            identifier=4, command_options={}, lookup_table=lookup_table,
            lookup_table_text=lookup_table_text, file_infos=file_infos,
            image_url=image_url)
        import_object_4.set_code('T_MOR010fr')
        import_object_4.created = datetime.now()
        import_object_4.wocat_data = {
            'table_1_1': [
                {
                    'column_1_1': 'French'
                }
            ],
            'table_3_1': [
                {
                    'column_3_1': 'wocat_value_3_2'
                }
            ],
            'table_25_1': [
                {
                    'column_25_1_1': 'Foo 1 French',
                    'column_25_1_2': 'Faz 1 French',
                },
                {
                    'column_25_1_1': 'Foo 2 French',
                    'column_25_1_2': 'Faz 2 French',
                }
            ],
            'table_25_2': [
                {
                    'column_25_2_1': 'Foo 3 French',
                    'column_25_2_2': 'Faz 3 French',
                },
                {
                    'column_25_2_1': 'Foo 4 French',
                },
            ],
            'table_27_1': [
                {
                    'column_27_1_1': 'un un',
                    'column_27_1_2': 'un deux',
                }
            ],
            'table_28_1': [
                {
                    'column_28_1_1': 'un',
                    'column_28_1_2': 'deux',
                    'column_28_1_3': 'trois'
                }
            ]
        }

        self.imprt.import_objects = [
            import_object_1,
            import_object_2,
            import_object_3,
            import_object_4,
        ]

    def tearDown(self):
        pass

    def test_mapping_empty(self):
        self.imprt.mapping = {}
        self.imprt.do_mapping()
        for import_object in self.imprt.import_objects:
            self.assertEqual(import_object.data_json, {})

    def test_mapping_non_existing(self):
        self.imprt.mapping = {
            'qg_1': {
                'questions': {
                    'question_1_1': {
                        'mapping': [
                            {
                                'wocat_table': 'foo',
                                'wocat_column': 'bar',
                            }
                        ],
                        'type': 'string',
                    }
                }
            }
        }
        self.imprt.do_mapping()
        for import_object in self.imprt.import_objects:
            self.assertEqual(import_object.data_json, {})

    def test_mapping_string(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_1'), [
            {
                'question_1_1': {
                    'en': 'Foo'
                }
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        self.assertIsNone(import_object_2.data_json.get('qg_1'))

    def test_mapping_multiple_strings(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_2'), [
            {
                'question_2_1': {
                    'en': 'Foo'
                },
                'question_2_2': {
                    'en': 'Bar'
                }
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        self.assertEqual(import_object_2.data_json.get('qg_2'), [
            {
                'question_2_1': {
                    'en': 'Faz'
                }
            }
        ])

    def test_mapping_dropdown_values(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_3'), [
            {
                'question_3_1': 'qcat_value_3_1'
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        self.assertEqual(import_object_2.data_json.get('qg_3'), [
            {
                'question_3_1': 'wocat_value_not_mapped'
            }
        ])

    def test_mapping_dropdown_values_prefix(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_4'), [
            {
                'question_4_1': 'qcat_value_4_1'
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        self.assertEqual(import_object_2.data_json.get('qg_4'), [
            {
                'question_4_1': 'prefix_wocat_value_not_mapped'
            }
        ])

    def test_mapping_date(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_5'), [
            {
                'question_5_1': '20/04/2010'
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        self.assertEqual(import_object_2.data_json.get('qg_5'), [
            {
                'question_5_1': '01/01/2000'
            }
        ])

    def test_mapping_constant(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_6'), [
            {
                'question_6_1': 1
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        self.assertEqual(import_object_2.data_json.get('qg_6'), [
            {
                'question_6_1': 1
            }
        ])

    def test_mapping_merge_strings(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_7'), [
            {
                'question_7_1': {
                    'en': 'First question: Foo\n\nSecond question: Bar'
                }
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        self.assertEqual(import_object_2.data_json.get('qg_7'), [
            {
                'question_7_1': {
                    'en': 'Second question: Faz'
                }
            }
        ])

    def test_mapping_merge_geom_points(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_8'), [
            {
                'question_8_1': json.dumps({
                    'type': 'FeatureCollection',
                    'features': [
                        {
                            'type': 'Feature',
                            'geometry': {
                                'type': 'Point',
                                'coordinates': [5.0, 46.0]
                            },
                            'properties': None
                        }
                    ]
                })
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        self.assertEqual(import_object_2.data_json.get('qg_8'), [
            {
                'question_8_1': json.dumps({
                    'type': 'FeatureCollection',
                    'features': [
                        {
                            'type': 'Feature',
                            'geometry': {
                                'type': 'Point',
                                'coordinates': [
                                    38.59791111111112, 38.59791111111112]
                            },
                            'properties': None
                        }
                    ]
                })
            }
        ])

    def test_mapping_merge_checkboxes(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        qg_data = import_object_1.data_json['qg_9']
        self.assertEqual(len(qg_data), 1)
        self.assertIn('value_9_1', qg_data[0]['question_9_1'])
        self.assertIn('value_9_3', qg_data[0]['question_9_1'])
        import_object_2 = self.imprt.import_objects[1]
        self.assertEqual(import_object_2.data_json.get('qg_9'), [
            {
                'question_9_1': ['value_9_2']
            }
        ])

    def test_mapping_merge_checkboxes_exclusive(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        qg_data = import_object_1.data_json['qg_10']
        self.assertEqual(len(qg_data), 1)
        self.assertIn('qcat_value_10_1', qg_data[0]['question_10_1'])
        self.assertIn('qcat_value_10_3', qg_data[0]['question_10_1'])
        import_object_2 = self.imprt.import_objects[1]
        qg_data = import_object_2.data_json['qg_10']
        self.assertEqual(len(qg_data), 1)
        self.assertEqual(len(qg_data[0]['question_10_1']), 1)
        self.assertIn('qcat_value_10_2', qg_data[0]['question_10_1'])

    def test_mapping_questiongroup_condition_matches(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_11'), [
            {
                'question_11_1': 'value_11_1'
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        self.assertIsNone(import_object_2.data_json.get('qg_11'))

    def test_mapping_merge_condition_matches(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_12'), [
            {
                'question_12_1': {
                    'en': 'Value 1: Foo\n\nValue 2: Bar'
                }
            }
        ])
        self.assertIn('Condition X was true.', import_object_1.mapping_messages)
        import_object_2 = self.imprt.import_objects[1]
        self.assertEqual(import_object_2.data_json.get('qg_12'), [
            {
                'question_12_1': {
                    'en': 'Value 2: Taz'
                }
            }
        ])

    def test_mapping_conditions_operators_join(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_13'), [
            {
                'question_13_1': {
                    'en': 'Value 1: Foo\n\nValue 2: Bar'
                }
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        self.assertEqual(import_object_2.data_json.get('qg_13'), [
            {
                'question_13_1': {
                    'en': 'Value 1: Foo'
                }
            }
        ])

    def test_mapping_conditions_is_empty(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_14'), [
            {
                'question_14_1': {
                    'en': 'Value 1: Foo\n\nValue 2: Bar'
                }
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        self.assertEqual(import_object_2.data_json.get('qg_14'), [
            {
                'question_14_1': {
                    'en': 'Value 2: Bar'
                }
            }
        ])

    def test_mapping_nested_string_mapping(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_15'), [
            {
                'question_15_1': {
                    'en': 'Value 1: Foo'
                },
                'question_15_2': {
                    'en': 'Value 2: Foo\n\nBar: Faz'
                }
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        self.assertEqual(import_object_2.data_json.get('qg_15'), [
            {
                'question_15_1': {
                    'en': 'Value 1: Foo'
                },
                'question_15_2': {
                    'en': 'Value 2: Foo\n\nFaz'
                }
            }
        ])

    def test_mapping_lookup_table(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_16'), [
            {
                'question_16_1': {
                    'en': 'English 1'
                },
                'question_16_2': {
                    'en': 'English 2\n\nEnglish 3'
                }
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        self.assertEqual(import_object_2.data_json.get('qg_16'), [
            {
                'question_16_1': {
                    'en': '4'
                },
                'question_16_2': {
                    'en': '5\n\n6'
                }
            }
        ])

    def test_mapping_merge_checkboxes_non_exclusive(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        qg_data = import_object_1.data_json['qg_17']
        self.assertEqual(len(qg_data), 1)
        self.assertIn('qcat_value_17_1', qg_data[0]['question_17_1'])
        self.assertIn('wocat_value_17_5', qg_data[0]['question_17_1'])
        import_object_2 = self.imprt.import_objects[1]
        qg_data = import_object_2.data_json['qg_17']
        self.assertEqual(len(qg_data), 1)
        self.assertEqual(len(qg_data[0]['question_17_1']), 2)
        self.assertIn('wocat_value_17_0', qg_data[0]['question_17_1'])
        self.assertIn('qcat_value_17_2', qg_data[0]['question_17_1'])

    def test_nested_condition(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_18'), [
            {
                'question_18_1': {
                    'en': 'Prefix: Value 18_1: Value 18_2',
                }
            }
        ])
        self.assertIn(
            'Question 18_1 shown', import_object_1.mapping_messages)
        import_object_2 = self.imprt.import_objects[1]
        self.assertIsNone(import_object_2.data_json.get('qg_18'))
        self.assertNotIn(
            'Question 18_1 shown', import_object_2.mapping_messages)

    def test_question_condition(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_19'), [
            {
                'question_19_1': 'true'
            }
        ])
        self.assertIn(
            'Question 19_1 shown', import_object_1.mapping_messages)
        import_object_2 = self.imprt.import_objects[1]
        self.assertIsNone(import_object_2.data_json.get('qg_19'))
        self.assertNotIn(
            'Question 19_1 shown', import_object_2.mapping_messages)

    def test_repeating_table(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_20'), [
            {
                'question_20_1': ['foo']
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        qg = import_object_2.data_json.get('qg_20')
        self.assertEqual(len(qg), 1)
        q = qg[0]['question_20_1']
        self.assertEqual(len(q), 2)
        self.assertIn('foo', q)
        self.assertIn('bar', q)

    def test_condition_equals(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_21'), [
            {
                'question_21_1': {
                    'en': 'Value 1\n\nValue 3'
                }
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        self.assertEqual(import_object_2.data_json.get('qg_21'), [
            {
                'question_21_1': {
                    'en': 'Value 1\n\nValue 2'
                }
            }
        ])

    def test_translation(self):
        initial_import_objects = len(self.imprt.import_objects)
        self.imprt.check_translations()
        # One import object (the translation) is removed
        self.assertEqual(
            len(self.imprt.import_objects), initial_import_objects - 1)
        self.imprt.do_mapping()
        import_object_3 = self.imprt.import_objects[2]
        self.assertEqual(import_object_3.data_json.get('qg_1'), [
            {
                'question_1_1': {
                    'en': 'English',
                    'fr': 'French'
                }
            }
        ])

    def test_translation_uses_dropdown_of_original(self):
        self.imprt.do_mapping()
        import_object_3 = self.imprt.import_objects[2]
        self.assertEqual(import_object_3.data_json.get('qg_3'), [
            {
                'question_3_1': 'qcat_value_3_1'
            }
        ])

    def test_conditional_row(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_22'), [
            {
                'question_22_1': {
                    'en': 'True'
                }
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        self.assertIsNone(import_object_2.data_json.get('qg_22'))

    def test_repeating_questiongroup(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        qg_data_1 = import_object_1.data_json.get('qg_23')
        self.assertEqual(len(qg_data_1), 2)
        self.assertEqual(qg_data_1[0], {
            'question_23_1': {
                'en': 'Foo 1',
            },
            'question_23_2': {
                'en': 'Faz 1',
            }
        })
        self.assertEqual(qg_data_1[1], {
            'question_23_1': {
                'en': 'Foo 2',
            },
            'question_23_2': {
                'en': 'Faz 2',
            }
        })

    def test_conditional_array(self):
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        self.assertEqual(import_object_1.data_json.get('qg_24'), [
            {
                'question_24_1': {
                    'en': 'Foo'
                }
            }
        ])
        import_object_2 = self.imprt.import_objects[1]
        self.assertEqual(import_object_2.data_json.get('qg_24'), [
            {
                'question_24_1': {
                    'en': 'Bar\n\nFaz'
                }
            }
        ])
        import_object_3 = self.imprt.import_objects[2]
        self.assertIsNone(import_object_3.data_json.get('qg_24'))

    def test_repeating_questiongroup_multiple_tables(self):
        self.imprt.check_translations()
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        qg_data_25 = import_object_1.data_json.get('qg_25')
        self.assertEqual(len(qg_data_25), 4)
        self.assertEqual(qg_data_25[0], {
            'question_25_1': {'en': 'Foo 3'},
            'question_25_2': {'en': 'Faz 3'},
            'question_25_3': '3',
            'question_25_4': 'value_2',
        })
        self.assertEqual(qg_data_25[1], {
            'question_25_1': {'en': 'Foo 4'},
            'question_25_2': {'en': 'Faz 4'},
            'question_25_3': '4',
            'question_25_4': 'value_2',
        })
        self.assertEqual(qg_data_25[2], {
            'question_25_1': {'en': 'Foo 2'},
            'question_25_2': {'en': 'Faz 2'},
            'question_25_3': '2',
            'question_25_4': 'value_1',
        })
        self.assertEqual(qg_data_25[3], {
            'question_25_1': {'en': 'Foo 1'},
            'question_25_2': {'en': 'Faz 1'},
            'question_25_3': '1',
            'question_25_4': 'value_1',
        })
        import_object_2 = self.imprt.import_objects[1]
        qg_data_25 = import_object_2.data_json.get('qg_25')
        self.assertEqual(len(qg_data_25), 4)
        self.assertEqual(qg_data_25[0], {
            'question_25_1': {'en': 'Foo 1'},
            'question_25_2': {'en': 'Faz 1'},
            'question_25_4': 'value_1',
        })
        self.assertEqual(qg_data_25[1], {
            'question_25_1': {'en': 'Foo 2'},
            'question_25_4': 'value_1',
        })
        self.assertEqual(qg_data_25[2], {
            'question_25_2': {'en': 'Faz 3'},
            'question_25_4': 'value_2',
        })
        self.assertEqual(qg_data_25[3], {
            'question_25_1': {'en': 'Foo 4'},
            'question_25_2': {'en': 'Faz 4'},
            'question_25_4': 'value_2',
        })
        import_object_3 = self.imprt.import_objects[2]
        qg_data_25 = import_object_3.data_json.get('qg_25')
        self.assertEqual(len(qg_data_25), 4)
        self.assertEqual(qg_data_25[0], {
            'question_25_1': {'en': 'Foo 1 English', 'fr': 'Foo 1 French'},
            'question_25_2': {'en': 'Faz 1 English', 'fr': 'Faz 1 French'},
            'question_25_4': 'value_1',
        })
        self.assertEqual(qg_data_25[1], {
            'question_25_1': {'en': 'Foo 2 English', 'fr': 'Foo 2 French'},
            'question_25_2': {'en': 'Faz 2 English', 'fr': 'Faz 2 French'},
            'question_25_4': 'value_1',
        })
        self.assertEqual(qg_data_25[2], {
            'question_25_1': {'en': 'Foo 3 English', 'fr': 'Foo 3 French'},
            'question_25_2': {'en': 'Faz 3 English', 'fr': 'Faz 3 French'},
            'question_25_4': 'value_2',
        })
        self.assertEqual(qg_data_25[3], {
            'question_25_1': {'en': 'Foo 4 English', 'fr': 'Foo 4 French'},
            'question_25_2': {'en': 'Faz 4 English'},
            'question_25_4': 'value_2',
        })
        self.assertIn(
            'Number of translations for table_25_2 in language "fr" do not '
            'match the number of original entries.',
            import_object_3.mapping_messages)

    def test_repeating_questiongroups_across_columns(self):
        self.imprt.check_translations()
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        qg_data_27 = import_object_1.data_json.get('qg_27')
        self.assertEqual(len(qg_data_27), 2)
        self.assertEqual(qg_data_27[0], {
            'question_27_1': {'en': 'one one\n\nOther: one two'}
        })
        self.assertEqual(qg_data_27[1], {
            'question_27_1': {'en': 'two one\n\nOther: two two'}
        })
        import_object_2 = self.imprt.import_objects[1]
        qg_data_27 = import_object_2.data_json.get('qg_27')
        self.assertIsNone(qg_data_27)
        import_object_3 = self.imprt.import_objects[2]
        qg_data_27 = import_object_3.data_json.get('qg_27')
        self.assertEqual(len(qg_data_27), 2)
        self.assertEqual(qg_data_27[0], {
            'question_27_1': {'en': 'one one\n\nOther: one two',
                              'fr': 'un un\n\nOther: un deux'}
        })
        self.assertEqual(qg_data_27[1], {
            'question_27_1': {'en': 'two one\n\nOther: two two'}
        })

    def test_repeating_questiongroups_across_columns_2(self):
        self.imprt.check_translations()
        self.imprt.do_mapping()
        import_object_1 = self.imprt.import_objects[0]
        qg_data_28 = import_object_1.data_json.get('qg_28')
        self.assertEqual(len(qg_data_28), 2)
        self.assertEqual(qg_data_28[0], {
            'question_28_1': {'en': 'one'}
        })
        self.assertEqual(qg_data_28[1], {
            'question_28_1': {'en': 'two'}
        })
        import_object_2 = self.imprt.import_objects[2]
        qg_data_28 = import_object_2.data_json.get('qg_28')
        self.assertEqual(len(qg_data_28), 3)
        self.assertEqual(qg_data_28[0], {
            'question_28_1': {'en': 'one', 'fr': 'un'}
        })
        self.assertEqual(qg_data_28[1], {
            'question_28_1': {'en': 'two', 'fr': 'deux'}
        })
        self.assertEqual(qg_data_28[2], {
            'question_28_1': {'fr': 'trois'}
        })

    # from nose.plugins.attrib import attr
    # @attr('foo')
    # def test_repeating_in_same_row(self):
    #     self.imprt.do_mapping()
    #     import_object_1 = self.imprt.import_objects[0]
    #     qg_data_26 = import_object_1.data_json.get('qg_26')
    #     self.assertEqual(qg_data_26, '')
    #     self.assertEqual(len(qg_data_26), 2)
