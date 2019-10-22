import copy

from django.utils.translation import ugettext_lazy as _

from .base import Edition, Operation


class Technologies(Edition):
    """
    Questionnaire updates for carbon benefit.
    """
    code = 'technologies'
    edition = 2018

    all_configuration_editions = [
        'technologies_2018', 'technologies', 'approaches', 'cca', 'watershed']

    @property
    def operations(self):
        return [
            Operation(
                transform_configuration=self.add_option_user_resourceperson_type,
                release_note=_('1.2: A new option "co-compiler" was added to question "Key resource persons".')
            ),
            Operation(
                transform_configuration=self.remove_person_address_questions,
                transform_questionnaire=self.delete_person_address_data,
                release_note=_('1.2: The questions "Address", "Phone" and "E-Mail" of "Key resource persons" were removed.')
            ),
            Operation(
                transform_configuration=self.move_date_documentation,
                transform_questionnaire=self.move_date_documentation_data,
                release_note=_('1.3: The question "Date of compilation in the field" was moved to 7.1.'),
            ),
            Operation(
                transform_configuration=self.remove_subcategory_1_6,
                release_note=''
            ),
            Operation(
                transform_configuration=self.do_nothing,
                # This happened in self.merge_subcategory_3_5_into_2_5 ...
                release_note=_('2.5: The questions about "Spread of the Technology" (previously in 3.5) were integrated into 2.5.')
            ),
            Operation(
                transform_configuration=self.do_nothing,
                # This happened in self.merge_subcategory_3_5_into_2_5 ...
                release_note=_('2.5: A new question "If precise area is known, please specify" was added.')
            ),
            Operation(
                transform_configuration=self.add_tech_location_protected,
                release_note=_('2.5: A new question "Is/are the technology site(s) located in a permanently protected area?" was added.')
            ),
            Operation(
                transform_configuration=self.update_map_template,
                release_note='',
            ),
            Operation(
                transform_configuration=self.add_tech_lu_mixed,
                transform_questionnaire=self.remove_tech_lu_mixed,
                release_note=_('3.2: A separate question about "Mixed land use" was added.')
            ),
            Operation(
                transform_configuration=self.add_questions_tech_lu_cropland,
                release_note=_('3.2: New questions about crops, intercropping and crop rotation for land use type "Cropland" were added.'),
            ),
            Operation(
                transform_configuration=self.remove_tech_lu_cropland_specify,
                transform_questionnaire=self.delete_tech_lu_cropland_specify_data,
                release_note=_('3.2: The question "Main crops" of land use type "Cropland" was removed.')
            ),
            Operation(
                transform_configuration=self.add_questions_tech_lu_grazingland,
                release_note=_('3.2: New questions about grazing land (animal type, crop-livestock management practices, products and services) were added.')
            ),
            Operation(
                transform_configuration=self.remove_tech_lu_grazingland_specify,
                transform_questionnaire=self.delete_tech_lu_grazingland_specify,
                release_note=_('3.2: The question "Main animal species and products" of land use type "Grazing land" was removed.')
            ),
            Operation(
                transform_configuration=self.add_tech_livestock_population,
                release_note=_('3.2: A new question "Livestock population" for land use type "Grazing land" was added.')
            ),
            Operation(
                transform_configuration=self.rename_tech_lu_grazingland_pastoralism,
                release_note=_('3.2: The option "semi-nomadism" of land use type "Grazing land" was renamed to "semi-nomadic pastoralism".')
            ),
            Operation(
                transform_configuration=self.add_option_tech_lu_grazingland_transhumant,
                release_note=_('3.2: A new option "transhumant pastoralism" was added to land use type "Grazing land".')
            ),
            Operation(
                transform_configuration=self.add_questions_tech_lu_woodlands,
                release_note=_('3.2: New questions about forest type and trees for land use type "Forest/ woodlands" were added.')
            ),
            Operation(
                transform_configuration=self.remove_tech_lu_change,
                transform_questionnaire=self.delete_tech_lu_change,
                release_note=_('3.2: The question "If land use has changed due to the implementation of the Technology, indicate land use before implementation of the Technology" was removed. This information can now be entered in 3.3.')
            ),
            Operation(
                transform_configuration=self.add_subcategory_initial_landuse,
                release_note=_('3.3 (new): A new subcategory about initial land use was added.')
            ),
            Operation(
                transform_configuration=self.move_tech_growing_seasons,
                transform_questionnaire=self.delete_tech_growing_seasons,
                release_note=_('3.4 (previously 3.3): The question "Number of growing seasons per year" was moved to 3.2 - land use type "Cropland". Data was migrated automatically only if land use type "Cropland" was selected.')
            ),
            Operation(
                transform_configuration=self.remove_tech_livestock_density,
                transform_questionnaire=self.delete_tech_livestock_density,
                release_note=_('3.4 (previously 3.3): The question "Livestock density (if relevant)" was removed. Use "Comments" of "3.2 Current land use type(s)".')
            ),
            Operation(
                transform_configuration=self.merge_subcategory_3_5_into_2_5,
                transform_questionnaire=self.delete_tech_spread_tech_comments,
                release_note=_('3.5: The previous questions of "3.5 Spread of the Technology" were integrated into "2.5 Country/ region/ locations where the Technology has been applied and which are covered by this assessment".')
            ),
            Operation(
                transform_configuration=self.do_nothing,
                # This happened in self.merge_subcategory_3_5_into_2_5 ...
                release_note=_('3.5: The question "Comments" about "Spread of the Technology" (previously 3.5) was removed; its content needs to be merged with "Comments" of 2.5.')
            ),
            Operation(
                transform_configuration=self.add_question_tech_agronomic_tillage,
                release_note=_('3.6: A new question "Differentiate tillage systems" was added when selecting agronomic measure "A3: Soil surface treatment".')
            ),
            Operation(
                transform_configuration=self.add_option_a6_residue_management,
                release_note=_('3.6: A new option "A6: Residue Management" was added to "agronomic measures".')
            ),
            Operation(
                transform_configuration=self.rename_option_a6_others,
                release_note=_('3.6 The option "A6: Others" of "agronomic measures" was renamed to "A7: Others".')
            ),
            Operation(
                transform_configuration=self.add_question_tech_residue_management,
                release_note=_('3.6: A new question "Specify residue management" was added when selecting agronomic measure "A6: residue management".')
            ),
            Operation(
                transform_configuration=self.add_other_measures_textfield,
                release_note=_('3.6: A new question to specify was added when selecting "other measures".')
            ),
            Operation(
                transform_configuration=self.add_other_degradation_textfield,
                release_note=_('3.7: A new question to specify was added when selecting other degradation type.')
            ),
            Operation(
                transform_configuration=self.do_nothing,
                release_note=_('4: The numbering was updated (4.2 was removed).')
            ),
            Operation(
                transform_configuration=self.move_technical_specification,
                transform_questionnaire=self.delete_technical_specification,
                release_note=_('4.1: The previous question "4.2 Technical specifications" was integrated into "4.1 Technical drawing".')
            ),
            Operation(
                transform_configuration=self.input_exchange_rate_change_template,
                release_note=''
            ),
            Operation(
                transform_configuration=self.remove_tech_est_type,
                transform_questionnaire=self.delete_tech_est_type,
                release_note=_('4.3 (previously 4.4): The question "Type of measure" was removed from Establishment activities.')
            ),
            Operation(
                transform_configuration=self.add_question_tech_input_est_total_costs_usd,
                release_note=_('4.4 (previously 4.5): A new question "Total costs for establishment of the Technology in USD" (automatically calculated) was added.')
            ),
            Operation(
                transform_configuration=self.remove_tech_maint_type,
                transform_questionnaire=self.delete_tech_maint_type,
                release_note=_('4.5 (previously 4.6): The question "Type of measure" was removed from Maintenance activities.')
            ),
            Operation(
                transform_configuration=self.add_question_tech_input_maint_total_costs_usd,
                release_note=_('4.6 (previously 4.7): A new question "Total costs for maintenance of the Technology in USD" (automatically calculated) was added.')
            ),
            Operation(
                transform_configuration=self.move_tech_input_est_total_estimation,
                release_note='',
            ),
            Operation(
                transform_configuration=self.rename_tech_input_est_total_estimation,
                release_note='',
            ),
            Operation(
                transform_configuration=self.move_tech_input_maint_total_estimation,
                release_note='',
            ),
            Operation(
                transform_configuration=self.rename_tech_input_maint_total_estimation,
                release_note='',
            ),
            Operation(
                transform_configuration=self.rename_tech_individuals,
                release_note='',
            ),
            Operation(
                transform_configuration=self.rename_us_dollars,
                release_note=''
            ),
            Operation(
                transform_configuration=self.reformat_agroclimatic_zone,
                release_note=''
            ),
            Operation(
                transform_configuration=self.add_question_water_quality_referring,
                release_note=_('5.4: A new question about water quality (referring to ground or surface water) was added.')
            ),
            Operation(
                transform_configuration=self.allow_more_options_age_land_users,
                release_note=_('5.6: More options for question "Age of land users" can be selected.')
            ),
            Operation(
                transform_configuration=self.add_question_tech_traditional_rights,
                release_note=_('5.8: A new question about traditional land use rights was added.')
            ),
            Operation(
                transform_configuration=self.add_comment_field_access,
                release_note=_('5.9: A new question for comments regarding "Access to services and infrastructure" was added.')
            ),
            Operation(
                transform_configuration=self.add_comment_field_onfield_impacts,
                release_note=_('6.1: A new question for comments about on-site impacts was added.')
            ),
            Operation(
                transform_configuration=self.add_general_comments_field,
                release_note=_('7.4 (new): A new question for general remarks about the questionnaire and feedback was added.')
            ),
            Operation(
                transform_configuration=self.various_translation_updates,
                release_note=''
            ),
            Operation(
                transform_configuration=self.add_new_LUT_listvalues,
                release_note=_(
                    'Update October 2019: Question 3.2: New Annual crops, Perennial crops, Tree/shrub crops, animal type, crop-livestock management practices, products and services, New forest plantation types, tree types and new species for "Livestock population" were added.'),
            ),
        ]

    def add_question_tech_input_maint_total_costs_usd(self, **data) -> dict:

        # Create a new question
        k_keyword = 'tech_input_maint_total_costs_usd'
        self.create_new_question(
            keyword=k_keyword,
            translation={
                'label': {
                    'en': 'Total costs for maintenance of the Technology in USD'
                }
            },
            question_type='float',
            configuration={
                'form_options': {
                    'label': 'placeholder',
                    'field_options': {
                        'min': 0,
                        'decimals': 2,
                        'readonly': 'readonly',
                        'data-local-currency-calculation': 'tech_qg_164|tech_input_exchange_rate|tech_qg_223|tech_input_maint_total_costs'
                    }
                }
            }
        )

        # Create new questiongroup and add the question to it.
        qg_keyword = 'tech_qg_233'
        self.create_new_questiongroup(
            keyword=qg_keyword, translation=None)
        qg_configuration = {
            'keyword': qg_keyword,
            'questions': [
                {
                    'keyword': k_keyword
                }
            ]
        }

        subcat_path = ('section_specifications', 'tech__4', 'tech__4__7')
        subcat_data = self.find_in_data(path=subcat_path, **data)

        # Update table grouping options
        subcat_data['view_options']['table_grouping'][1] += [qg_keyword]

        # Add the questiongroup
        questiongroups = subcat_data['questiongroups']

        questiongroups.insert(8, qg_configuration)
        subcat_data['questiongroups'] = questiongroups

        data = self.update_config_data(
            path=subcat_path, updated=subcat_data, **data)

        return data

    def add_question_tech_input_est_total_costs_usd(self, **data) -> dict:

        # Create a new question
        k_keyword = 'tech_input_est_total_costs_usd'
        self.create_new_question(
            keyword=k_keyword,
            translation={
                'label': {
                    'en': 'Total costs for establishment of the Technology in USD'
                }
            },
            question_type='float',
            configuration={
                'form_options': {
                    'label': 'placeholder',
                    'field_options': {
                        'min': 0,
                        'decimals': 2,
                        'readonly': 'readonly',
                        'data-local-currency-calculation': 'tech_qg_164|tech_input_exchange_rate|tech_qg_222|tech_input_est_total_costs'
                    }
                }
            }
        )

        # Create new questiongroup and add the question to it.
        qg_keyword = 'tech_qg_232'
        self.create_new_questiongroup(
            keyword=qg_keyword, translation=None)
        qg_configuration = {
            'keyword': qg_keyword,
            'questions': [
                {
                    'keyword': k_keyword
                }
            ]
        }

        subcat_path = ('section_specifications', 'tech__4', 'tech__4__5')
        subcat_data = self.find_in_data(path=subcat_path, **data)

        # Update table grouping options
        subcat_data['view_options']['table_grouping'][1] += [qg_keyword]

        # Add the questiongroup
        questiongroups = subcat_data['questiongroups']
        questiongroups.insert(8, qg_configuration)
        subcat_data['questiongroups'] = questiongroups

        data = self.update_config_data(
            path=subcat_path, updated=subcat_data, **data)

        return data

    def delete_tech_spread_tech_comments(self, **data) -> dict:
        return self.update_data('tech_qg_4', 'tech_spread_tech_comments', None, **data)

    def merge_subcategory_3_5_into_2_5(self, **data) -> dict:

        old_subcat_path = ('section_specifications', 'tech__3', 'tech__3__5')
        old_subcat_data = self.find_in_data(path=old_subcat_path, **data)

        questiongroup = old_subcat_data['questiongroups'][0]  # There is only 1

        # Remove the entire old subcategory
        old_cat_path = ('section_specifications', 'tech__3')
        old_cat_data = self.find_in_data(path=old_cat_path, **data)
        old_cat_data['subcategories'] = [
            s for s in old_cat_data['subcategories']
            if s['keyword'] != 'tech__3__5'
        ]
        data = self.update_config_data(
            path=old_cat_path, updated=old_cat_data, **data)

        # Delete comments question of questiongroup
        questiongroup['questions'] = [
            q for q in questiongroup['questions'] if
            q['keyword'] != 'tech_spread_tech_comments']

        # Update translation of previous question about categorized area
        self.update_translation(
            update_pk=1311,
            **{
                "label": {
                    "en": "If precise area is not known, indicate approximate area covered"
                }
            }
        )

        # Add new question
        q_keyword = 'tech_spread_area_precise'
        self.create_new_question(
            keyword=q_keyword,
            translation={
                'label': {
                    'en': 'If the Technology is evenly spread over an area, specify area covered (in km2)'
                },
                'helptext': {
                    'en': '1 ha = 10’000m²; 1 km² = 100 ha'
                }
            },
            question_type='float',
            configuration={
                'summary': {
                    'types': ['full'],
                    'default': {
                        'field_name': 'location_spread_area_precise'
                    }
                }
            }
        )
        question_configuration = {
            'keyword': q_keyword,
            'form_options': {
                'field_options': {
                    'min': 0
                },
                'question_condition': 'tech_spread_area',
            }
        }

        new_questions = questiongroup['questions']
        new_questions.insert(1, question_configuration)
        questiongroup['questions'] = new_questions

        new_subcat_path = ('section_specifications', 'tech__2', 'tech__2__5')
        new_subcat_data = self.find_in_data(path=new_subcat_path, **data)

        # Add to questiongroups of new subcategory
        new_questiongroups = new_subcat_data['questiongroups']
        new_questiongroups.insert(3, questiongroup)
        new_subcat_data['questiongroups'] = new_questiongroups

        data = self.update_config_data(
            path=new_subcat_path, updated=new_subcat_data, **data)

        return data

    def allow_more_options_age_land_users(self, **data) -> dict:
        q_path = (
            'section_specifications', 'tech__5', 'tech__5__6', 'tech_qg_71',
            'tech_age_landusers')
        q_data = self.find_in_data(path=q_path, **data)
        q_data['form_options'] = {
            'field_options': {
                'data-cb-max-choices': 4
            }
        }
        data = self.update_config_data(path=q_path, updated=q_data, **data)
        return data

    def add_question_water_quality_referring(self, **data) -> dict:
        q_keyword = 'tech_waterquality_referring'
        self.create_new_question(
            keyword=q_keyword,
            translation={
                'label': {
                    'en': 'Water quality refers to:'
                }
            },
            question_type='radio',
            values=[
                self.create_new_value(
                    keyword='tech_waterquality_ref_ground',
                    translation={
                        'label': {
                            'en': 'ground water'
                        }
                    },
                    order_value=1
                ),
                self.create_new_value(
                    keyword='tech_waterquality_ref_surface',
                    translation={
                        'label': {
                            'en': 'surface water'
                        }
                    },
                    order_value=2
                ),
                self.create_new_value(
                    keyword='tech_waterquality_ref_both',
                    translation={
                        'label': {
                            'en': 'both ground and surface water'
                        }
                    },
                    order_value=3
                )
            ],
            configuration={
                "summary": {
                    "types": ["full"],
                    "default": {
                        "field_name": "natural_env_waterquality_ref",
                    }
                }
            }
        )

        qg_path = (
            'section_specifications', 'tech__5', 'tech__5__4', 'tech_qg_60')
        qg_data = self.find_in_data(path=qg_path, **data)

        qg_data['questions'] += [{
            'keyword': q_keyword,
            'view_options': {
                'template': 'inline_6'
            }
        }]
        return self.update_config_data(path=qg_path, updated=qg_data, **data)

    def add_comment_field_onfield_impacts(self, **data) -> dict:

        subcat_path = ('section_specifications', 'tech__6', 'tech__6__1')
        subcat_data = self.find_in_data(path=subcat_path, **data)

        subcat_keyword = 'tech__6__1__comments'
        qg_keyword = 'tech_qg_252'
        q_keyword = 'tech_onsite_impacts_comments'
        self.create_new_category(
            keyword=subcat_keyword,
            translation={
                'label': {
                    'en': 'Comments'
                }
            }
        )
        self.create_new_questiongroup(
            keyword=qg_keyword,
            translation=None
        )
        self.create_new_question(
            keyword=q_keyword,
            translation={
                'label': {
                    'en': 'Specify assessment of on-site impacts (measurements)'
                }
            },
            question_type='text'
        )

        subcat_data['subcategories'] += [{
            'keyword': subcat_keyword,
            'form_options': {
                'template': 'empty'
            },
            'view_options': {
                'template': 'empty'
            },
            'questiongroups': [
                {
                    'keyword': qg_keyword,
                    'questions': [
                        {
                            'keyword': q_keyword,
                            'form_options': {
                                'label_class': 'top-margin'
                            },
                        }
                    ]
                }
            ]
        }]

        return self.update_config_data(
            path=subcat_path, updated=subcat_data, **data)

    def add_comment_field_access(self, **data) -> dict:

        qg_keyword = 'tech_qg_251'
        self.create_new_questiongroup(
            keyword=qg_keyword,
            translation=None
        )
        k_keyword = 'tech_access_comments'
        self.create_new_question(
            keyword=k_keyword,
            translation=5004,
            question_type='text',
            configuration={
                "summary": {
                    "types": ["full"],
                    "default": {
                        "field_name": "human_env_services_comments",
                    }
                }
            }
        )
        subcat_path = ('section_specifications', 'tech__5', 'tech__5__9')
        subcat_data = self.find_in_data(path=subcat_path, **data)
        subcat_data['questiongroups'] += [
            {
                'keyword': qg_keyword,
                'questions': [
                    {
                        'keyword': k_keyword
                    }
                ]
            }
        ]
        return self.update_config_data(
            path=subcat_path, updated=subcat_data, **data)

    def add_question_tech_traditional_rights(self, **data) -> dict:

        q_keyword = 'tech_traditional_rights'
        self.create_new_question(
            keyword=q_keyword,
            translation={
                'label': {
                    'en': 'Are land use rights based on a traditional legal system?'
                }
            },
            question_type='bool'
        )
        question_configuration = {
            'keyword': q_keyword,
            'form_options': {
                'question_conditions': [
                    '=="1"|tech_traditional_rights_specify'
                ]
            }
        }

        q_keyword_specify = 'tech_traditional_rights_specify'
        self.create_new_question(
            keyword=q_keyword_specify,
            translation={
                'label': {
                    'en': 'Specify'
                }
            },
            question_type='text'
        )
        question_specify_configuration = {
            'keyword': q_keyword_specify,
            'form_options': {
                'question_condition': 'tech_traditional_rights_specify'
            }
        }

        qg_path = ('section_specifications', 'tech__5', 'tech__5__8', 'tech_qg_73')
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['questions'] += [question_configuration, question_specify_configuration]

        return self.update_config_data(path=qg_path, updated=qg_data, **data)

    def move_technical_specification(self, **data) -> dict:

        # Add tech_specifications to 4.1
        qg_path = (
            'section_specifications', 'tech__4', 'tech__4__1', 'tech_qg_185')
        qg_data = self.find_in_data(path=qg_path, **data)

        # Show label as placeholder of text area
        tech_specs = {
            'keyword': 'tech_specifications',
            'form_options': {
                'label_position': 'placeholder',
            }
        }

        qg_data['questions'].insert(1, tech_specs)
        # Adjust template and update max_num
        qg_data['form_options'].update({
            'template': 'columns_custom',
            'columns_custom': [['12'], ['12'], ['6', '6']],
            'max_num': 10
        })
        data = self.update_config_data(path=qg_path, updated=qg_data, **data)

        # Update translation of tech_specifications (insert helptext previously
        # in subcategory)
        self.update_translation(
            update_pk=1036,
            **{
                "label": {
                    "en": "Technical specifications (related to technical drawing)"
                },
                "helptext": {
                    "en": "<p>Summarize technical specifications, e.g.:</p><ul><li>Dimensions (height, depth, width, length) of structures or vegetative elements;</li><li>Spacing between structures or plants/ vegetative measures</li><li>Vertical intervals structures or vegetative measures</li><li>Slope angle (before and after implementation of the Technology)</li><li>Lateral gradient of structures</li><li>Capacity of dams, ponds, etc.</li><li>Catchment area and beneficial area of dams, ponds, other water harvesting systems</li><li>Construction material used</li><li>Species used</li><li>Quantity/ density of plants (per ha)</li></ul>"
                }
            }
        )

        # Remove 4.2
        cat_path = (
            'section_specifications', 'tech__4')
        cat_data = self.find_in_data(path=cat_path, **data)
        new_subcats = []
        for subcat in cat_data['subcategories']:
            # Exclude 4.2
            if subcat['keyword'] == 'tech__4__2':
                continue

            # Update numbering
            if subcat['keyword'] != 'tech__4__1':
                old_numbering = subcat['form_options']['numbering']
                new_numbering = str(round(float(old_numbering) - 0.1, 1))
                subcat['form_options']['numbering'] = new_numbering

            new_subcats.append(subcat)
        cat_data['subcategories'] = new_subcats
        data = self.update_config_data(path=cat_path, updated=cat_data, **data)

        # Update helptexts of new subcategories 4.4 and 4.6 (pointing to
        # previous subcategories where numbering has changed)
        self.update_translation(
            update_pk=2792,
            **{
                "label": {
                    "en": "Costs and inputs needed for establishment"
                },
                "helptext": {
                    "en": "<p><strong>Note</strong>: Costs and inputs specified in this question should refer to the technology area/ technology unit defined in 4.2 and to the activities listed in 4.3. Use the currency indicated in 4.2.</p><p>Figures reflect the situation at the time of recording the data.</p>"
                }
            }
        )
        self.update_translation(
            update_pk=2793,
            **{
                "label": {
                    "en": "Costs and inputs needed for maintenance/ recurrent activities (per year)"
                },
                "helptext": {
                    "en": "<p><strong>Note</strong>: Costs and inputs specified in this question should refer to the technology area/ technology unit defined in 4.2, and to the activities listed in 4.5. Use the currency indicated in 4.2.</p><p>Figures reflect the situation at the time of recording the data.</p>"
                }
            }
        )

        return data

    def delete_technical_specification(self, **data) -> dict:
        if 'tech_qg_161' in data:
            del data['tech_qg_161']
        return data

    def input_exchange_rate_change_template(self, **data) -> dict:
        q_path = (
            'section_specifications', 'tech__4', 'tech__4__3', 'tech_qg_164',
            'tech_input_exchange_rate')
        q_data = self.find_in_data(path=q_path, **data)
        q_data['form_options']['template'] = 'currency_exchange_rate'
        data = self.update_config_data(path=q_path, updated=q_data, **data)
        return data

    def update_map_template(self, **data) -> dict:
        # Update the template used to render the map (do not show the label).
        q_path = ('section_specifications', 'tech__2', 'tech__2__5',
                  'qg_location_map', 'location_map')
        q_data = self.find_in_data(path=q_path, **data)
        q_data['form_options'] = {
            'template': 'no_label'
        }
        return self.update_config_data(path=q_path, updated=q_data, **data)

    def add_tech_location_protected(self, **data) -> dict:
        qg_keyword = 'tech_qg_234'
        self.create_new_questiongroup(
            keyword=qg_keyword,
            translation=None
        )
        question_keyword = 'tech_location_protected'
        self.create_new_question(
            keyword=question_keyword,
            translation={
                'label': {
                    'en': 'Is/are the technology site(s) located in a permanently protected area?'
                },
                'helptext': {
                    'en': 'I.e. national reserve/ national park'
                }
            },
            question_type='bool',
            configuration={
                'summary': {
                    'types': ['full'],
                    'default': {
                        'field_name': 'location_protected_area'
                    }
                }
            }
        )
        specify_keyword = 'tech_location_protected_specify'
        self.create_new_question(
            keyword=specify_keyword,
            translation={
                'label': {
                    'en': 'If yes, specify'
                }
            },
            question_type='text',
        )
        qg_configuration = {
            'keyword': qg_keyword,
            'questions': [
                {
                    'keyword': question_keyword,
                    'form_options': {
                        'question_conditions': [
                            f"=='1'|{specify_keyword}"
                        ],
                        'helptext_position': 'tooltip'
                    }
                },
                {
                    'keyword': specify_keyword,
                    'form_options': {
                        'question_condition': specify_keyword
                    }
                }
            ]
        }
        subcat_path = ('section_specifications', 'tech__2', 'tech__2__5')
        subcat_data = self.find_in_data(path=subcat_path, **data)
        questiongroups = subcat_data['questiongroups']
        questiongroups.insert(3, qg_configuration)
        subcat_data['questiongroups'] = questiongroups
        return self.update_config_data(path=subcat_path, updated=subcat_data, **data)

    def remove_tech_lu_mixed(self, **data) -> dict:

        # Migrate values of tech_landuse to tech_landuse_2018 (tech_qg_9)
        new_landuse_qg = []
        for landuse_qg in data.get('tech_qg_9', []):
            new_lu_values = [
                v for v in landuse_qg.get('tech_landuse', [])
                if v != 'tech_lu_mixed']
            landuse_qg['tech_landuse_2018'] = new_lu_values
            del landuse_qg['tech_landuse']
            new_landuse_qg.append(landuse_qg)
        data['tech_qg_9'] = new_landuse_qg

        # Remove entire questiongroup tech_qg_13
        if 'tech_qg_13' in data:
            del data['tech_qg_13']

        return data

    def add_tech_lu_mixed(self, **data) -> dict:

        subcat_path = ('section_specifications', 'tech__3', 'tech__3__2')
        subcat_data = self.find_in_data(path=subcat_path, **data)

        # Remove tech_lu_mixed from questiongroup_conditions
        subcat_data['form_options']['questiongroup_conditions'] = [
            c for c in subcat_data['form_options']['questiongroup_conditions']
            if c != "=='tech_lu_mixed'|tech_qg_13"
        ]

        # Remove questiongroup tech_qg_13 (lu_mixed)
        subcat_data['questiongroups'] = [
            qg for qg in subcat_data['questiongroups']
            if qg['keyword'] != 'tech_qg_13'
        ]
        data = self.update_config_data(
            path=subcat_path, updated=subcat_data, **data)

        # Remove tech_lu_mixed from questiongroup_conditions (of tech_qg_9)
        old_cond_qg_path = (
            'section_specifications', 'tech__3', 'tech__3__2', 'tech_qg_9')
        old_cond_qg_data = self.find_in_data(path=old_cond_qg_path, **data)
        old_cond_qg_data['questions'][0]['form_options']['questiongroup_conditions'] = [
            c for c in old_cond_qg_data['questions'][0]['form_options']['questiongroup_conditions']
            if c != "=='tech_lu_mixed'|tech_qg_13"
        ]

        # Instead of removing value "tech_lu_mixed" of question "tech_landuse",
        # create a new question "tech_landuse_2018". Just deleting the value
        # from the existing question would mean that technologies in the
        # previous edition would also automatically have this value removed,
        # which is not correct behaviour.
        old_question = self.get_question(keyword='tech_landuse')
        old_configuration = old_question.configuration
        old_configuration['form_options']['field_options']['data-cb-max-choices'] = 3
        # Use custom method to extract values in summary.
        old_configuration['summary']['default']['get_value'] = {'name': 'get_landuse_2018_values'}
        old_configuration['summary']['default']['field_name'] = 'classification_landuse_current'
        new_keyword = 'tech_landuse_2018'
        self.create_new_question(
            keyword=new_keyword,
            translation={
                "label": {
                    "en": "Select land use type"
                },
                "label_view": {
                    "en": "Land use type"
                }
            },
            question_type='image_checkbox',
            values=[
                self.get_value(keyword='tech_lu_cropland'),
                self.get_value(keyword='tech_lu_grazingland'),
                self.get_value(keyword='tech_lu_forest'),
                self.get_value(keyword='tech_lu_settlements'),
                self.get_value(keyword='tech_lu_waterways'),
                self.get_value(keyword='tech_lu_mines'),
                self.get_value(keyword='tech_lu_unproductive'),
                self.get_value(keyword='tech_lu_other'),
            ],
            configuration=old_configuration,
        )
        old_cond_qg_data['questions'][0]['keyword'] = new_keyword
        data = self.update_config_data(
            path=old_cond_qg_path, updated=old_cond_qg_data, **data)

        # Add new question about mixed land use at the beginning of the
        # subcategory

        # Update the translations of the values
        self.update_translation(
            update_pk=1512,
            **{
                'label': {
                    'en': 'Agroforestry'
                },
                'helptext': {
                    'en': '<strong>Mf: Agroforestry</strong>: cropland and trees.<br>Select "Cropland" and "Forest/ woodlands" below and fill out the relevant sections.'
                }
            }
        )
        self.update_translation(
            update_pk=1513,
            **{
                'label': {
                    'en': 'Agro-pastoralism (incl. integrated crop-livestock)'
                },
                'helptext': {
                    'en': '<strong>Mp: Agro-pastoralism</strong>: cropland and grazing land (including seasonal change between crops and livestock).<br>Select "Cropland" and "Grazing land" below and fill out the relevant sections.'
                }
            }
        )
        self.update_translation(
            update_pk=1514,
            **{
                'label': {
                    'en': 'Agro-silvopastoralism'
                },
                'helptext': {
                    'en': '<strong>Ma: Agro-silvopastoralism</strong>: cropland, grazing land and trees (including seasonal change between crops and livestock).<br>Select "Cropland", "Grazing land" and "Forest/ woodlands" below and fill out the relevant sections.'
                }
            }
        )
        self.update_translation(
            update_pk=1515,
            **{
                'label': {
                    'en': 'Silvo-pastoralism'
                },
                'helptext': {
                    'en': '<strong>Ms: Silvo-pastoralism</strong>: forest and grazing land.<br>Select "Grazing land" and "Forest/ woodlands" below and fill out the relevant sections.'
                }
            }
        )
        new_mixed_keyword = 'tech_lu_mixed'
        self.create_new_question(
            keyword=new_mixed_keyword,
            translation={
                'label': {
                    'en': 'Is land use mixed within the same land unit (e.g. agroforestry)?'
                },
                'label_view': {
                    'en': 'Land use mixed within the same land unit:'
                },
                'helptext': {
                    'en': 'A mixture of crops, grazing and trees within the same land unit, e.g. agroforestry, agro-silvopastoralism.'
                },
            },
            question_type='bool',
            configuration={
                'summary': {
                    'types': ['full'],
                    'default': {
                        'field_name': 'landuse_current_mixed',
                        'get_value': {
                            'name': 'get_landuse_mixed_values'
                        }
                    }
                }
            }
        )

        new_mixed_keyword_specify = 'tech_lu_mixed_select'
        self.create_new_question(
            keyword=new_mixed_keyword_specify,
            translation={
                'label': {
                    'en': 'Specify mixed land use (crops/ grazing/ trees)'
                },
            },
            question_type='radio',
            values=[
                self.get_value('lu_mixed_mf'),
                self.get_value('lu_mixed_mp'),
                self.get_value('lu_mixed_ma'),
                self.get_value('lu_mixed_ms'),
            ]
        )

        new_qg_keyword = 'tech_qg_235'
        self.create_new_questiongroup(
            keyword=new_qg_keyword,
            translation=None
        )

        subcat_data = self.find_in_data(path=subcat_path, **data)
        subcat_data['questiongroups'] = [
            {
                'keyword': new_qg_keyword,
                'questions': [
                    {
                        'keyword': new_mixed_keyword,
                        'form_options': {
                            'question_conditions': [
                                f"=='1'|{new_mixed_keyword_specify}"
                            ],
                            'helptext_position': 'tooltip',
                        }
                    },
                    {
                        'keyword': new_mixed_keyword_specify,
                        'form_options': {
                            'question_condition': new_mixed_keyword_specify,
                        }
                    }
                ]
            }
        ] + subcat_data['questiongroups']
        subcat_data['form_options']['template'] = 'tech_lu_2018'

        self.update_translation(
            update_pk=2781,
            **{
                "label": {
                    "en": "Current land use type(s) where the Technology is applied"
                },
                "helptext": {
                    "en": "<p><strong>Land use</strong>: human activities which are directly related to land, making use of its resources or having an impact upon it.<br><strong>Land cover</strong>: Vegetation (natural or planted) or man-made structures (buildings, etc.) that cover the earth’s surface.</p>"
                }
            }
        )

        data = self.update_config_data(
            path=subcat_path, updated=subcat_data, **data)

        return data

    def add_questions_tech_lu_woodlands(self, **data) -> dict:

        qg_path = (
            'section_specifications', 'tech__3', 'tech__3__2', 'tech_qg_12'
        )
        qg_data = self.find_in_data(path=qg_path, **data)

        # Update the "other" question to have the label appear as placeholder
        qg_data['questions'][2]['form_options']['label_position'] = 'placeholder'
        del qg_data['questions'][2]['form_options']['row_class']

        # Update the conditions of the sub checkbox questions
        qg_data['questions'][0]['form_options']['question_condition'] = 'tech_lu_forest_natural'
        qg_data['questions'][1]['form_options']['question_condition'] = 'tech_lu_forest_plantation'

        # Update the translations of these questions
        self.update_translation(
            update_pk=1339,
            **{
                'label': {
                    'en': '(Semi-)natural forests/ woodlands: Specify management type'
                }
            }
        )
        self.update_translation(
            update_pk=1240,
            **{
                'label': {
                    'en': 'Tree plantation, afforestation: Specify origin and composition of species'
                }
            }
        )

        # Create a new first checkbox question which triggers the conditions
        forest_question_keyword = 'tech_lu_forest_type'
        forest_value_natural = 'lu_forest_natural'
        forest_value_plantation = 'lu_forest_plantation'
        self.create_new_question(
            keyword=forest_question_keyword,
            translation={},
            question_type='checkbox',
            values=[
                self.create_new_value(
                    keyword=k,
                    translation={
                        'label': {
                            'en': l
                        },
                        'helptext': {
                            'en': h
                        }
                    }
                )
                for i, (k, l, h) in enumerate([
                    (forest_value_natural, '(Semi-)natural forests/ woodlands', '<strong>Fn: Natural or semi-natural</strong>: forests mainly composed of indigenous trees, not planted by man'),
                    (forest_value_plantation, 'Tree plantation, afforestation', '<strong>Fp: Plantations, afforestations:</strong>: forest stands established by planting or/ and seeding in the process of afforestation or reforestation'),
                ])
            ]
        )
        qg_data['questions'] += [
            {
                'keyword': forest_question_keyword,
                'form_options': {
                    'template': 'no_label',
                    'question_conditions': [
                        f"=='{forest_value_natural}'|tech_lu_forest_natural",
                        f"=='{forest_value_plantation}'|tech_lu_forest_plantation",
                    ]
                },
                'view_options': {
                    'label_position': 'none'
                }
            }
        ]
        data = self.update_config_data(path=qg_path, updated=qg_data, **data)

        # Add new question about type of forest (natural)
        type_natural_keyword = 'tech_lu_forest_natural_type'
        data = self._create_land_use_subquestions(
            qg_path=qg_path,
            keyword=type_natural_keyword,
            label='(Semi-)natural forests/ woodlands: Specify type of forest',
            label_view='Type of (semi-)natural forest',
            values_list=[
                ('natural_forest_1715', 'boreal coniferous forest natural vegetation'),
                ('natural_forest_1716', 'boreal mountain systems natural vegetation'),
                ('natural_forest_1717', 'boreal tundra woodland natural vegetation'),
                ('natural_forest_1750', 'subtropical desert natural vegetation'),
                ('natural_forest_1751', 'subtropical dry forest natural vegetation'),
                ('natural_forest_1752', 'subtropical humid forest natural vegetation'),
                ('natural_forest_1753', 'subtropical mountain systems natural vegetation'),
                ('natural_forest_1754', 'subtropical steppe natural vegetation'),
                ('natural_forest_1758', 'temperate continental forest natural vegetation'),
                ('natural_forest_1759', 'temperate desert natural vegetation'),
                ('natural_forest_1760', 'temperate mountain systems natural vegetation'),
                ('natural_forest_1761', 'temperate oceanic forest natural vegetation'),
                ('natural_forest_1762', 'temperate steppe natural vegetation'),
                ('natural_forest_1765', 'tropical desert natural vegetation'),
                ('natural_forest_1766', 'tropical dry forest natural vegetation'),
                ('natural_forest_1767', 'tropical moist deciduous forest natural vegetation'),
                ('natural_forest_1768', 'tropical mountain systems natural vegetation'),
                ('natural_forest_1769', 'tropical rain forest natural vegetation'),
                ('natural_forest_1770', 'tropical shrubland natural vegetation'),
            ],
            other_label='If type of forest is not listed above, specify other type',
            conditional_value=None,
            question_condition_keyword='tech_lu_forest_natural',
            **data
        )

        # Add new question about type of forest (plantation)
        type_plantation_keyword = 'tech_lu_forest_plantation_type'
        data = self._create_land_use_subquestions(
            qg_path=qg_path,
            keyword=type_plantation_keyword,
            label='Tree plantation, afforestation: Specify type of forest',
            label_view='Type of tree plantation, afforestation',
            values_list=[
                ('plantation_forest_1773', 'boreal coniferous forest plantation'),
                ('plantation_forest_1774', 'boreal mountain systems plantation'),
                ('plantation_forest_1775', 'boreal tundra woodland plantation'),
                ('plantation_forest_1776', 'subtropical dry forest plantation'),
                ('plantation_forest_1777', 'subtropical dry forest plantation - Eucalyptus spp.'),
                ('plantation_forest_1779', 'subtropical dry forest plantation - Broadleaf'),
                ('plantation_forest_1780', 'subtropical dry forest plantation - Pinus spp.'),
                ('plantation_forest_1781', 'subtropical dry forest plantation - Tectona grandis'),
                ('plantation_forest_1782', 'subtropical humid forest plantation - broadleaf'),
                ('plantation_forest_1783', 'subtropical humid forest plantation - Eucalyptus spp.'),
                ('plantation_forest_1784', 'subtropical humid forest plantation'),
                ('plantation_forest_1786', 'subtropical humid forest plantation - Pinus spp.'),
                ('plantation_forest_1787', 'subtropical humid forest plantation - Tectona grandis'),
                ('plantation_forest_1788', 'subtropical mountain systems plantation - broadleaf'),
                ('plantation_forest_1789', 'subtropical mountain systems plantation - Eucalyptus spp.'),
                ('plantation_forest_1790', 'subtropical mountain systems plantation'),
                ('plantation_forest_1792', 'subtropical mountain systems plantation - Pinus spp.'),
                ('plantation_forest_1793', 'subtropical mountain systems plantation - Tectona grandis'),
                ('plantation_forest_1794', 'subtropical steppe plantation'),
                ('plantation_forest_1795', 'subtropical steppe plantation - broadleaf'),
                ('plantation_forest_1796', 'subtropical steppe plantation - coniferous'),
                ('plantation_forest_1797', 'subtropical steppe plantation - Eucalyptus spp.'),
                ('plantation_forest_1799', 'subtropical steppe plantation - Pinus spp.'),
                ('plantation_forest_1800', 'subtropical steppe plantation - Tectona grandis'),
                ('plantation_forest_1801', 'temperate continental forest plantation'),
                ('plantation_forest_1802', 'temperate mountain systems plantation'),
                ('plantation_forest_1803', 'temperate oceanic forest plantation'),
                ('plantation_forest_steppe', 'temperate steppe plantation'),
                ('plantation_forest_1804', 'tropical dry forest plantation - broadleaf'),
                ('plantation_forest_1805', 'tropical dry forest plantation - Eucalyptus spp.'),
                ('plantation_forest_1806', 'tropical dry forest plantation'),
                ('plantation_forest_1808', 'tropical dry forest plantation - Pinus spp.'),
                ('plantation_forest_1809', 'tropical dry forest plantation - Tectona grandis'),
                ('plantation_forest_1810', 'tropical moist deciduous forest plantation - broadleaf'),
                ('plantation_forest_1811', 'tropical moist deciduous forest plantation - Eucalyptus spp.'),
                ('plantation_forest_1812', 'tropical moist deciduous forest plantation'),
                ('plantation_forest_1814', 'tropical moist deciduous forest plantation - Pinus spp.'),
                ('plantation_forest_1815', 'tropical moist deciduous forest plantation - Tectona grandis'),
                ('plantation_forest_1816', 'tropical mountain systems plantation - broadleaf'),
                ('plantation_forest_1817', 'tropical mountain systems plantation - Eucalyptus spp.'),
                ('plantation_forest_1818', 'tropical mountain systems plantation'),
                ('plantation_forest_1820', 'tropical mountain systems plantation - Pinus spp.'),
                ('plantation_forest_1821', 'tropical mountain systems plantation - Tectona grandis'),
                ('plantation_forest_1822', 'tropical rain forest plantation'),
                ('plantation_forest_1823', 'tropical rain forest plantation - broadleaf'),
                ('plantation_forest_1824', 'tropical rain forest plantation - Eucalyptus spp.'),
                ('plantation_forest_1827', 'tropical rain forest plantation - Pinus spp.'),
                ('plantation_forest_1828', 'tropical rain forest plantation - Tectona grandis'),
                ('plantation_forest_1829', 'tropical shrubland plantation'),
                ('plantation_forest_1830', 'tropical shrubland plantation - broadleaf'),
                ('plantation_forest_1831', 'tropical shrubland plantation - Eucalyptus spp.'),
                ('plantation_forest_1833', 'tropical shrubland plantation - Pinus spp.'),
            ],
            other_label='If type of forest is not listed above, specify other type',
            conditional_value=None,
            question_condition_keyword='tech_lu_forest_plantation',
            **data
        )

        # Add new question about type of trees
        type_tree_keyword = 'tech_lu_forest_tree_type'
        data = self._create_land_use_subquestions(
            qg_path=qg_path,
            keyword=type_tree_keyword,
            label='Specify type of tree',
            label_view='Type of tree',
            values_list=[
                ('tree_type_1700', 'Acacia albida'),
                ('tree_type_1701', 'Acacia auriculiformis'),
                ('tree_type_1702', 'Acacia mearnsii'),
                ('tree_type_1703', 'Acacia mellifera'),
                ('tree_type_1704', 'Acacia nilotica'),
                ('tree_type_1705', 'Acacia senegal'),
                ('tree_type_1706', 'Acacia seyal'),
                ('tree_type_1707', 'Acacia species'),
                ('tree_type_1708', 'Acacia tortilis'),
                ('tree_type_1709', 'Ailanthus excelsa'),
                ('tree_type_1710', 'Ailanthus species'),
                ('tree_type_1711', 'Araucaria angustifolia'),
                ('tree_type_1712', 'Araucaria cunninghamii'),
                ('tree_type_1713', 'Balanites aegyptiaca'),
                ('tree_type_1714', 'Bamboo bamboo'),
                ('tree_type_1718', 'Casuarina equisetifolia'),
                ('tree_type_1719', 'Casuarina junghuhniana'),
                ('tree_type_1720', 'Cordia alliadora'),
                ('tree_type_1721', 'Cupressus lusitanica'),
                ('tree_type_1722', 'Cupressus species'),
                ('tree_type_1723', 'Dalbergia sissoo'),
                ('tree_type_1724', 'Eucalyptus camaldulensis'),
                ('tree_type_1725', 'Eucalyptus deglupta'),
                ('tree_type_1726', 'Eucalyptus globulus'),
                ('tree_type_1727', 'Eucalyptus grandis'),
                ('tree_type_1728', 'Eucalyptus robusta'),
                ('tree_type_1729', 'Eucalyptus saligna'),
                ('tree_type_1730', 'Eucalyptus species'),
                ('tree_type_1731', 'Eucalyptus urophylla'),
                ('tree_type_1732', 'Abies species (fir)'),
                ('tree_type_1733', 'Gmelina arborea'),
                ('tree_type_1734', 'Hevea brasiliensis'),
                ('tree_type_1735', 'Khaya species'),
                ('tree_type_1736', 'Larix species (larch)'),
                ('tree_type_1737', 'Leucaena leucocephala'),
                ('tree_type_1738', 'Mimosa scabrella'),
                ('tree_type_1739', 'Pinus species (pine)'),
                ('tree_type_1740', 'Pinus caribaea v. caribaea'),
                ('tree_type_1741', 'Pinus caribaea v. hondurensis'),
                ('tree_type_1742', 'Pinus oocarpa'),
                ('tree_type_1743', 'Pinus patula'),
                ('tree_type_1744', 'Pinus radiata'),
                ('tree_type_1745', 'Pinus species'),
                ('tree_type_1747', 'Populus species'),
                ('tree_type_1748', 'Sclerocarya birrea'),
                ('tree_type_1749', 'Picea species (spruce)'),
                ('tree_type_1755', 'Swietenia macrophylla'),
                ('tree_type_1756', 'Tectona grandis'),
                ('tree_type_1757', 'Tectona species'),
                ('tree_type_1763', 'Terminalia ivorensis'),
                ('tree_type_1764', 'Terminalia superba'),
                ('tree_type_1771', 'Xylia xylocapa'),
                ('tree_type_1772', 'Ziziphus mauritiana'),
                ('tree_type_1834', 'Azadirachta indica'),
                ('tree_type_1835', 'Grevillea robusta'),
            ],
            other_label='If type of tree is not listed above, specify other type',
            conditional_value=None,
            **data
        )

        # Add new question about decidiuous or evergreen trees
        deciduous_trees_keyword = 'tech_lu_forest_deciduous'
        self.create_new_question(
            keyword=deciduous_trees_keyword,
            translation={
                'label': {
                    'en': 'Are the trees specified above deciduous or evergreen?'
                }
            },
            question_type='radio',
            values=[
                self.create_new_value(
                    keyword=k,
                    translation={
                        'label': {
                            'en': l
                        }
                    },
                    order_value=i
                )
                for i, (k, l) in enumerate([
                    ('trees_deciduous', 'deciduous'),
                    ('trees_deciduous_mixed', 'mixed deciduous/ evergreen'),
                    ('trees_evergreen', 'evergreen'),
                ])
            ]
        )
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['questions'] += [
            {
                'keyword': deciduous_trees_keyword,
                'form_options': {
                    'row_class': 'top-margin',
                }
            }
        ]

        # Rearrange order of questions
        order = [
            forest_question_keyword,
            'tech_lu_sub_other',
            'tech_lu_forest_natural',
            type_natural_keyword,
            f'{type_natural_keyword}_other',
            'tech_lu_forest_plantation',
            type_plantation_keyword,
            f'{type_plantation_keyword}_other',
            type_tree_keyword,
            f'{type_tree_keyword}_other',
            deciduous_trees_keyword,
            'tech_lu_forest_products',
            'tech_lu_forest_other',
        ]
        qg_data['questions'] = sorted(
            qg_data['questions'], key=lambda q: order.index(q['keyword']))

        data = self.update_config_data(path=qg_path, updated=qg_data, **data)

        return data

    def add_questions_tech_lu_grazingland(self, **data) -> dict:
        qg_path = (
            'section_specifications', 'tech__3', 'tech__3__2', 'tech_qg_11'
        )

        # Search animal type
        data = self._create_land_use_subquestions(
            qg_path=qg_path,
            keyword='tech_lu_grazingland_animals',
            label='Specify animal type',
            label_view='Animal type',
            values_list=[
                ('animals_50', 'cattle - dairy'),
                ('animals_51', 'cattle - non-dairy beef'),
                ('animals_52', 'cattle - non-dairy working'),
                ('animals_53', 'buffalo'),
                ('animals_54', 'swine'),
                ('animals_55', 'goats'),
                ('animals_56', 'camels'),
                ('animals_57', 'horses'),
                ('animals_58', 'mules and asses'),
                ('animals_59', 'sheep'),
                ('animals_60', 'poultry'),
                ('animals_61', 'rabbits and similar mammals'),
                ('animals_wildlife_large', 'wildlife - large herbivours'),
                ('animals_wildlife_small', 'wildlife - small herbivours'),
                ('animals_livestock_other_large', 'livestock - other large'),
                ('animals_livestock_other_small', 'livestock - other small'),
            ],
            other_label='If animal type is not listed above, specify other animal',
            conditional_value=None,
            **data
        )

        # Crop-livestock management
        crop_livestock_keyword = 'tech_crop_livestock_management'
        crop_livestock_specify_keyword = 'tech_crop_livestock_management_specify'
        self.create_new_question(
            keyword=crop_livestock_keyword,
            translation={
                'label': {
                    'en': 'Is integrated crop-livestock management practiced?'
                },
                'helptext': {
                    'en': '<strong>Integrated crop-livestock management</strong>: crops and livestock interact to create synergies, making optimal use of resources. The waste products of one component serve as a resource for the other (manure, fodder).'
                }
            },
            question_type='bool',
            configuration={
                'form_options': {
                    'helptext_position': 'tooltip'
                }
            }
        )
        self.create_new_question(
            keyword=crop_livestock_specify_keyword,
            translation={
                'label': {
                    'en': 'If yes, specify'
                }
            },
            question_type='text'
        )
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['questions'] = qg_data['questions'] + [
            {
                'keyword': crop_livestock_keyword,
                'form_options': {
                    'question_conditions': [
                        f"=='1'|{crop_livestock_specify_keyword}"
                    ],
                    'row_class': 'top-margin',
                }
            },
            {
                'keyword': crop_livestock_specify_keyword,
                'form_options': {
                    'question_condition': crop_livestock_specify_keyword
                }
            },
        ]

        # Products and services
        data = self._create_land_use_subquestions(
            qg_path=qg_path,
            keyword='tech_lu_grazingland_products',
            label='Specify products and services for grazing land',
            label_view='Products and services',
            values_list=[
                ('prod_service_meat', 'meat'),
                ('prod_service_milk', 'milk'),
                ('prod_service_eggs', 'eggs'),
                ('prod_service_whool', 'whool'),
                ('prod_service_skins', 'skins/ hides'),
                ('prod_service_transport', 'transport/  draught'),
            ],
            other_label='If product or service is not listed above, specify other product or service',
            conditional_value=None,
            **data
        )

        return data

    def add_tech_livestock_population(self, **data) -> dict:

        subcat_path = ('section_specifications', 'tech__3', 'tech__3__2')
        subcat_data = self.find_in_data(path=subcat_path, **data)

        # Create new questions
        keyword_species = 'tech_lu_grazingland_pop_species'
        keyword_count = 'tech_lu_grazingland_pop_count'
        self.create_new_question(
            keyword=keyword_species,
            translation={
                'label': {
                    'en': 'Species'
                }
            },
            question_type='select_type',
            values=[
                self.get_value('animals_50'),
                self.get_value('animals_51'),
                self.get_value('animals_52'),
                self.get_value('animals_53'),
                self.get_value('animals_54'),
                self.get_value('animals_55'),
                self.get_value('animals_56'),
                self.get_value('animals_57'),
                self.get_value('animals_58'),
                self.get_value('animals_59'),
                self.get_value('animals_60'),
                self.get_value('animals_61'),
                self.get_value('animals_wildlife_large'),
                self.get_value('animals_wildlife_small'),
            ]
        )
        self.create_new_question(
            keyword=keyword_count,
            translation={
                'label': {
                    'en': 'Count'
                }
            },
            question_type='int',
            configuration={
                'form_options': {
                    'field_options': {
                        'min': 0,
                    }
                }
            }
        )

        qg_keyword = 'tech_qg_236'
        self.create_new_questiongroup(
            keyword=qg_keyword,
            translation={
                'label': {
                    'en': 'Livestock population',
                }
            },
        )

        questiongroups = subcat_data['questiongroups']
        questiongroups.insert(4, {
            'keyword': qg_keyword,
            'form_options': {
                'questiongroup_condition': qg_keyword,
                'max_num': 5,
                'template': 'table1',
                'column_widths': ['70%', '30%'],
            },
            'view_options': {
                'conditional_question': 'tech_lu_grazingland',
            },
            'questions': [
                {
                    'keyword': keyword_species,
                },
                {
                    'keyword': keyword_count,
                }
            ]
        })
        subcat_data['questiongroups'] = questiongroups

        # Add conditions
        condition = f"=='tech_lu_grazingland'|{qg_keyword}"
        subcat_data['form_options']['questiongroup_conditions'] += [condition]
        subcat_data['questiongroups'][1]['questions'][0]['form_options'][
            'questiongroup_conditions'] += [condition]

        # Update template used for subcategory details
        subcat_data['view_options']['template'] = 'image_questiongroups_2018'

        data = self.update_config_data(
            path=subcat_path, updated=subcat_data, **data)

        return data

    def remove_tech_lu_grazingland_specify(self, **data) -> dict:
        qg_path = ('section_specifications', 'tech__3', 'tech__3__2', 'tech_qg_11')
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['questions'] = [
            q for q in qg_data['questions']
            if q['keyword'] != 'tech_lu_grazingland_specify'
        ]
        return self.update_config_data(path=qg_path, updated=qg_data, **data)

    def delete_tech_lu_grazingland_specify(self, **data) -> dict:
        return self.update_data(
            'tech_qg_11', 'tech_lu_grazingland_specify', None, **data)

    def remove_tech_lu_cropland_specify(self, **data) -> dict:
        qg_path = ('section_specifications', 'tech__3', 'tech__3__2', 'tech_qg_10')
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['questions'] = [
            q for q in qg_data['questions']
            if q['keyword'] != 'tech_lu_cropland_specify'
        ]
        return self.update_config_data(path=qg_path, updated=qg_data, **data)

    def delete_tech_lu_cropland_specify_data(self, **data) -> dict:
        return self.update_data(
            'tech_qg_10', 'tech_lu_cropland_specify', None, **data)

    def add_questions_tech_lu_cropland(self, **data) -> dict:
        qg_path = (
            'section_specifications', 'tech__3', 'tech__3__2', 'tech_qg_10'
        )

        # Annual cropping list of crops
        data = self._create_land_use_subquestions(
            qg_path=qg_path,
            keyword='tech_lu_cropland_annual_cropping_crops',
            label='Annual cropping - Specify crops',
            values_list=[
                ('annual_crops_422', 'cereals - barley'),
                ('annual_crops_429', 'cereals - maize'),
                ('annual_crops_430', 'cereals - millet'),
                ('annual_crops_431', 'cereals - oats'),
                ('annual_crops_452', 'cereals - other'),
                ('annual_crops_468', 'cereals - quinoa or amaranth'),
                ('annual_crops_436', 'cereals - rice (wetland)'),
                ('annual_crops_437', 'cereals - rice (upland)'),
                ('annual_crops_438', 'cereals - rye'),
                ('annual_crops_439', 'cereals - sorghum'),
                ('annual_crops_444', 'cereals - wheat (winter)'),
                ('annual_crops_445', 'cereals - wheat (spring)'),
                ('annual_crops_446', 'fibre crops - cotton'),
                ('annual_crops_453', 'fibre crops - flax, hemp, other'),
                ('annual_crops_flower', 'flower crops'),
                ('annual_crops_421', 'fodder crops - alfalfa'),
                ('annual_crops_425', 'fodder crops - clover'),
                ('annual_crops_455', 'fodder crops - grasses'),
                ('annual_crops_fodder_other', 'fodder crops - other'),
                ('annual_crops_423', 'legumes and pulses - beans'),
                ('annual_crops_457', 'legumes and pulses - other'),
                ('annual_crops_434', 'legumes and pulses - peas'),
                ('annual_crops_440', 'legumes and pulses - soya'),
                ('annual_crops_medicinal', 'medicinal/ aromatic/ pesticidal plants and herbs'),
                ('annual_crops_451', 'oilseed crops - castor'),
                ('annual_crops_456', 'oilseed crops - groundnuts'),
                ('annual_crops_464', 'oilseed crops -  sunflower, rapeseed, other'),
                ('annual_crops_435', 'root/tuber crops - potatoes'),
                ('annual_crops_424', 'root/tuber crops - cassava'),
                ('annual_crops_443', 'root/tuber crops - sugar beet'),
                ('annual_crops_467', 'root/tuber crops -  sweet potatoes, yams, taro/cocoyam, other'),
                ('annual_crops_470', 'seed crops - sesame, poppy, mustard, other'),
                ('annual_crops_473', 'tobacco'),
                ('annual_crops_428', 'vegetables - jerusalem artichoke'),
                ('annual_crops_vegetables_leafy', 'vegetables - leafy vegetables (salads, cabbage, spinach, other)'),
                ('annual_crops_462', 'vegetables - melon, pumpkin, squash or gourd'),
                ('annual_crops_463', 'vegetables - mushrooms and truffles'),
                ('annual_crops_vegetables_other', 'vegetables - other'),
                ('annual_crops_469', 'vegetables - root vegetables (carrots, onions, beet, other)'),
            ],
            other_label='If crop type is not listed above, specify other crop',
            conditional_value='lu_cropland_ca',
            **data
        )

        # Search cropping system
        cropping_system_keyword = 'tech_lu_cropland_cropping_system'
        self.create_new_question(
            keyword=cropping_system_keyword,
            translation={
                'label': {
                    'en': 'If data will be linked to CBP (simple assessment), specify annual cropping system'
                },
                'label_view': {
                    'en': 'Annual cropping system'
                }
            },
            question_type='select_type',
            values=self.create_new_values_list([
                ('cropping_system_401', 'Continuous wheat/barley/oats/upland rice'),
                ('cropping_system_402', 'Fallow - wheat/barley/oats/upland rice'),
                ('cropping_system_403', 'Continuous maize/sorghum/millet'),
                ('cropping_system_404', 'Fallow - maize/sorghum/millet'),
                ('cropping_system_405', 'Maize/sorghum/millet legume'),
                ('cropping_system_406', 'Maize/sorghum/millet intercropped with legume'),
                ('cropping_system_407', 'Fallow - maize/sorghum/millet intercropped with legume'),
                ('cropping_system_408', 'Continuous wetland rice'),
                ('cropping_system_409', 'Wetland rice - wheat'),
                ('cropping_system_410', 'Continuous vegetables'),
                ('cropping_system_411', 'Vegetables - wheat/barley/oat/upland rice'),
                ('cropping_system_412', 'Continuous cotton/tobacco'),
                ('cropping_system_413', 'Vegetable - cotton/tobacco'),
                ('cropping_system_414', 'Continuous root crop'),
                ('cropping_system_415', 'Cassava/potato/manioc - vegetable'),
                ('cropping_system_416', 'Cassava/potato/manioc - wheat/barley/oat'),
                ('cropping_system_417', 'Cassava/potato/manioc - maize/sorghum/millet'),
                ('cropping_system_418', 'Hay'),
                ('cropping_system_419', 'Wheat or similar rotation with hay/pasture'),
                ('cropping_system_420', 'Maize or similar rotation with hay/pasture'),
            ])
        )
        cropping_system_configuration = {
            'keyword': cropping_system_keyword,
            'form_options': {
                'question_condition': 'tech_lu_cropland_annual_cropping_crops',
            }
        }
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['questions'] = qg_data['questions'] + [
            cropping_system_configuration]
        data = self.update_config_data(path=qg_path, updated=qg_data, **data)

        # Perennial cropping list of crops
        data = self._create_land_use_subquestions(
            qg_path=qg_path,
            keyword='tech_lu_cropland_perennial_cropping_crops',
            label='Perennial (non-woody) cropping - Specify crops',
            values_list=[
                ('perennial_crops_502', 'banana/plantain/abaca'),
                ('perennial_crops_520', 'agave / sisal'),
                ('perennial_crops_521', 'areca'),
                ('perennial_crops_522', 'berries'),
                ('perennial_crops_sugar_cane', 'sugar cane'),
                ('perennial_crops_pineapple', 'pineapple'),
                ('perennial_crops_flower_crops', 'flower crops - perennial'),
                ('perennial_crops_medicinal', 'medicinal, aromatic, pesticidal plants - perennial'),
            ],
            other_label='If crop type is not listed above, specify other crop',
            conditional_value='lu_cropland_cp',
            **data
        )

        # Tree and shrub cropping list of crops
        data = self._create_land_use_subquestions(
            qg_path=qg_path,
            keyword='tech_lu_cropland_tree_shrub_cropping_crops',
            label='Tree and shrub cropping - Specify crops',
            values_list=[
                ('tree_shrub_501', 'avocado'),
                ('tree_shrub_503', 'citrus'),
                ('tree_shrub_504', 'cacao'),
                ('tree_shrub_505', 'coconut (fruit, coir, leaves, etc.)'),
                ('tree_shrub_506', 'coffee, open grown'),
                ('tree_shrub_507', 'coffee, shade grown'),
                ('tree_shrub_508', 'dates'),
                ('tree_shrub_509', 'mango, mangosteen, guava'),
                ('tree_shrub_510', 'oil palm'),
                ('tree_shrub_511', 'papaya'),
                ('tree_shrub_512', 'pome fruits (apples, pears, quinces, etc.)'),
                ('tree_shrub_513', 'rubber'),
                ('tree_shrub_514', 'stone fruits (peach, apricot, cherry, plum, etc)'),
                ('tree_shrub_515', 'tea'),
                ('tree_shrub_516', 'tree nuts (brazil nuts, pistachio, walnuts, almonds, etc.)'),
                ('tree_shrub_517', 'wolfberries'),
                ('tree_shrub_523', 'carob'),
                ('tree_shrub_524', 'cashew'),
                ('tree_shrub_525', 'cinnamon'),
                ('tree_shrub_528', 'figs'),
                ('tree_shrub_529', 'fruits, other'),
                ('tree_shrub_530', 'grapes'),
                ('tree_shrub_531', 'gums'),
                ('tree_shrub_532', 'jojoba'),
                ('tree_shrub_533', 'kapok'),
                ('tree_shrub_534', 'karite (sheanut)'),
                ('tree_shrub_535', 'olive'),
                ('tree_shrub_537', 'tallowtree'),
                ('tree_shrub_540', 'tung'),
                ('tree_shrub_fodder', 'fodder trees (Calliandra, Leucaena leucocephala, Prosopis, etc.)'),
            ],
            other_label='If crop type is not listed above, specify other crop',
            conditional_value='lu_cropland_ct',
            **data
        )

        # Add questions about intercropping and crop rotation
        intercropping_keyword = 'tech_intercropping'
        intercropping_specify_keyword = 'tech_intercropping_specify'
        self.create_new_question(
            keyword=intercropping_keyword,
            translation={
                'label': {
                    'en': 'Is intercropping practiced?'
                }
            },
            question_type='bool'
        )
        self.create_new_question(
            keyword=intercropping_specify_keyword,
            translation={
                'label': {
                    'en': 'If yes, specify which crops are intercropped'
                }
            },
            question_type='text'
        )
        croprotation_keyword = 'tech_crop_rotation'
        croprotation_specify_keyword = 'tech_crop_rotation_specify'
        self.create_new_question(
            keyword=croprotation_keyword,
            translation={
                'label': {
                    'en': 'Is crop rotation practiced?'
                }
            },
            question_type='bool'
        )
        self.create_new_question(
            keyword=croprotation_specify_keyword,
            translation={
                'label': {
                    'en': 'If yes, specify'
                },
                'helptext': {
                    'en': 'E.g. sequence of crops, fallow periods, green manuring'
                }
            },
            question_type='text'
        )
        qg_path = qg_path
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['questions'] = qg_data['questions'] + [
            {
                'keyword': intercropping_keyword,
                'form_options': {
                    'question_conditions': [
                        f"=='1'|{intercropping_specify_keyword}"
                    ],
                    'row_class': 'top-margin',
                }
            },
            {
                'keyword': intercropping_specify_keyword,
                'form_options': {
                    'question_condition': intercropping_specify_keyword
                }
            },
            {
                'keyword': croprotation_keyword,
                'form_options': {
                    'question_conditions': [
                        f"=='1'|{croprotation_specify_keyword}"
                    ],
                    'row_class': 'top-margin',
                }
            },
            {
                'keyword': croprotation_specify_keyword,
                'form_options': {
                    'question_condition': croprotation_specify_keyword,
                    'helptext_position': 'tooltip'
                }
            }
        ]
        data = self.update_config_data(path=qg_path, updated=qg_data, **data)
        return data

    def delete_tech_growing_seasons(self, **data) -> dict:

        moved_questions = {}
        for qg_data in data.get('tech_qg_19', []):
            remaining_data = {}
            for key, value in qg_data.items():
                if key in [
                    'tech_growing_seasons', 'tech_growing_seasons_specify'
                ]:
                    moved_questions[key] = value
                else:
                    remaining_data[key] = value
            if remaining_data:
                data['tech_qg_19'] = [remaining_data]
            else:
                del data['tech_qg_19']

        if moved_questions:
            # Only move data if the corresponding conditional value
            # (tech_lu_cropland of tech_qg_9.tech_landuse_2018) is selected.
            # Otherwise, do not move the data (as this would block the form from
            # being submitted)
            cond_question_values = []
            cond_question_values_qg = data.get('tech_qg_9')
            if cond_question_values_qg and len(cond_question_values_qg) > 0:
                cond_question_values = cond_question_values_qg[0].get(
                    'tech_landuse_2018', [])
            if 'tech_lu_cropland' in cond_question_values:
                new_data = data.get('tech_qg_10', [{}])
                new_data[0].update(moved_questions)
                data['tech_qg_10'] = new_data

        return data

    def remove_tech_lu_change(self, **data) -> dict:
        qg_path = ('section_specifications', 'tech__3', 'tech__3__2', 'tech_qg_7')
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['questions'] = [
            q for q in qg_data['questions']
            if q['keyword'] != 'tech_lu_change'
        ]
        return self.update_config_data(path=qg_path, updated=qg_data, **data)

    def add_subcategory_initial_landuse(self, **data) -> dict:
        cat_path = ('section_specifications', 'tech__3')
        cat_data = self.find_in_data(path=cat_path, **data)

        # New subcategory 3.3
        subcat_keyword = 'tech__3__3__initial_landuse'
        self.create_new_category(
            keyword=subcat_keyword,
            translation={
                'label': {
                    'en': 'Has land use changed due to the implementation of the Technology?'
                },
                'helptext': {
                    'en': 'This section is not relevant for traditional systems'
                }
            }
        )

        # New question about whether land use has changed
        qg_keyword = 'tech_qg_237'
        self.create_new_questiongroup(
            keyword=qg_keyword,
            translation=None
        )
        q_keyword = 'tech_initial_landuse_changed'
        self.create_new_question(
            keyword=q_keyword,
            translation={
                'label': {
                    'en': 'Has land use changed due to the implementation of the Technology?'
                }
            },
            question_type='radio',
            values=self.create_new_values_list([
                ('initial_landuse_changed_yes', 'Yes (Please fill out the questions below with regard to the land use before implementation of the Technology)'),
                ('initial_landuse_changed_no', 'No (Continue with question 3.4)')
            ]),
            configuration={
                'summary': {
                    'types': ['full'],
                    'default': {
                        'field_name': 'initial_landuse_changed',
                        'get_value': {
                            'name': 'get_initial_landuse_changed'
                        }
                    }
                }
            }
        )

        # Basically copy subcategory 3.2
        original_subcat_path = ('section_specifications', 'tech__3', 'tech__3__2')
        original_subcat_data = self.find_in_data(path=original_subcat_path, **data)
        original_qgs = copy.deepcopy(original_subcat_data['questiongroups'])

        # Re-map the questiongroups to ones newly created
        qg_mapping = {
            'tech_qg_235': 'tech_qg_238',  # mixed landuse?
            'tech_qg_9': 'tech_qg_239',    # main checkbox about land use
            'tech_qg_10': 'tech_qg_240',   # cropland (details)
            'tech_qg_11': 'tech_qg_241',   # grazingland (details)
            'tech_qg_236': 'tech_qg_242',  # grazingland (details, population)
            'tech_qg_12': 'tech_qg_243',   # forest (details)
            'tech_qg_14': 'tech_qg_244',   # settlements (details)
            'tech_qg_15': 'tech_qg_245',   # waterways (details)
            'tech_qg_16': 'tech_qg_246',   # mines (details)
            'tech_qg_17': 'tech_qg_247',   # unproductive (details)
            'tech_qg_18': 'tech_qg_248',   # other (details)
            'tech_qg_7': 'tech_qg_249',    # comments
        }
        # Re-map conditions
        questiongroup_conditions = [
            "=='tech_lu_cropland'|tech_qg_240",
            "=='tech_lu_grazingland'|tech_qg_241",
            "=='tech_lu_forest'|tech_qg_243",
            "=='tech_lu_settlements'|tech_qg_244",
            "=='tech_lu_waterways'|tech_qg_245",
            "=='tech_lu_mines'|tech_qg_246",
            "=='tech_lu_unproductive'|tech_qg_247",
            "=='tech_lu_other'|tech_qg_248",
            "=='tech_lu_grazingland'|tech_qg_242"
        ]

        new_qgs = []
        for qg in original_qgs:
            # Create a new questiongroup, use previous translation
            new_qg_keyword = qg_mapping[qg['keyword']]
            original_qg = self.get_questiongroup(qg['keyword'])
            self.create_new_questiongroup(
                keyword=new_qg_keyword,
                translation=original_qg.translation
            )
            qg['keyword'] = new_qg_keyword

            # Update questiongroup_condition where relevant
            if new_qg_keyword in [
                'tech_qg_240',
                'tech_qg_241',
                'tech_qg_243',
                'tech_qg_244',
                'tech_qg_245',
                'tech_qg_246',
                'tech_qg_247',
                'tech_qg_248',
                'tech_qg_242',
            ]:
                qg['form_options']['questiongroup_condition'] = new_qg_keyword

            # Update conditions of subquestions
            for question in qg['questions']:
                question_conditions = question.get('form_options', {}).get('question_conditions', [])
                if question_conditions:
                    question['form_options']['question_conditions'] = [
                        f'{cond}_initial' for cond in question_conditions
                    ]
                question_condition = question.get('form_options', {}).get('question_condition')
                if question_condition:
                    question['form_options']['question_condition'] = f'{question_condition}_initial'

                if question['keyword'] == 'tech_lu_mixed':
                    question['summary'] = {
                        'types': ['full'],
                        'default': {
                            'field_name': 'landuse_initial_mixed',
                            'get_value': {
                                'name': 'get_landuse_mixed_values'
                            }
                        }
                    }

            # Add questiongroup conditions to land use question, as well as
            # summary information.
            if qg['questions'][0]['keyword'] == 'tech_landuse_2018':
                qg['questions'][0]['summary'] = {
                    'types': ['full'],
                    'default': {
                        'get_value': {
                            'name': 'get_landuse_2018_values'
                        },
                        'field_name': 'classification_landuse_initial'
                    }
                }
                qg['questions'][0]['form_options']['questiongroup_conditions'] = questiongroup_conditions
                # Remove initial land use from filter. Otherwise, there would be
                # two questions with the same label in the filter. And it was
                # never a requirement that initial land use is filterable.
                qg['questions'][0]['filter_options'] = {'order': None}

            new_qgs.append(qg)

        # Configuration of new subcategory
        subcategory_data = {
            'keyword': subcat_keyword,
            'form_options': {
                'numbering': '3.3',
                'questiongroup_conditions': questiongroup_conditions,
                'template': 'tech_lu_2018'
            },
            'view_options': {
                'raw_questions': True,
                'template': 'image_questiongroups_2018'
            },
            'questiongroups': [
                {
                    'keyword': qg_keyword,
                    'form_options': {
                        'helptext_position': 'bottom',
                    },
                    'questions': [
                        {
                            'keyword': q_keyword,
                        }
                    ]
                }
            ] + new_qgs
        }
        # Insert at correct position
        subcategories = cat_data['subcategories']
        subcategories.insert(2, subcategory_data)
        cat_data['subcategories'] = subcategories
        data = self.update_config_data(path=cat_path, updated=cat_data, **data)

        # Update numbering of following subcategories (3.5 was removed,
        # therefore numbering of 3.6 and following stays the same)
        subcat_path = ('section_specifications', 'tech__3', 'tech__3__3')
        subcat_data = self.find_in_data(path=subcat_path, **data)
        subcat_data['form_options']['numbering'] = '3.4'
        data = self.update_config_data(
            path=subcat_path, updated=subcat_data, **data)

        subcat_path = ('section_specifications', 'tech__3', 'tech__3__4')
        subcat_data = self.find_in_data(path=subcat_path, **data)
        subcat_data['form_options']['numbering'] = '3.5'
        data = self.update_config_data(
            path=subcat_path, updated=subcat_data, **data)

        # Update translation of 3.4 (previously Further information about land
        # use)
        self.update_translation(
            update_pk=2788,
            **{
                'label': {
                    'en': 'Water supply'
                }
            }
        )

        return data

    def delete_tech_lu_change(self, **data) -> dict:
        return self.update_data('tech_qg_7', 'tech_lu_change', None, **data)

    def remove_tech_livestock_density(self, **data) -> dict:
        qg_path = ('section_specifications', 'tech__3', 'tech__3__3', 'tech_qg_19')
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['questions'] = [
            q for q in qg_data['questions']
            if q['keyword'] != 'tech_livestock_density'
        ]
        return self.update_config_data(path=qg_path, updated=qg_data, **data)

    def delete_tech_livestock_density(self, **data) -> dict:
        return self.update_data(
            'tech_qg_19', 'tech_livestock_density', None, **data)

    def move_tech_growing_seasons(self, **data) -> dict:

        # Remove questions from old questiongroup
        old_qg_path = (
            'section_specifications', 'tech__3', 'tech__3__3', 'tech_qg_19')
        old_qg_data = self.find_in_data(path=old_qg_path, **data)
        old_qg_data['questions'] = [
            q for q in old_qg_data['questions']
            if q['keyword'] not in [
                'tech_growing_seasons', 'tech_growing_seasons_specify'
            ]
        ]
        data = self.update_config_data(
            path=old_qg_path, updated=old_qg_data, **data)

        # Add questions to new questiongroup
        new_qg_path = (
            'section_specifications', 'tech__3', 'tech__3__2', 'tech_qg_10')
        new_qg_data = self.find_in_data(path=new_qg_path, **data)

        questions = new_qg_data['questions']
        position = 9
        questions.insert(position, {
            'keyword': 'tech_growing_seasons_specify'
        })
        questions.insert(position, {
            'keyword': 'tech_growing_seasons',
            'form_options': {
                'row_class': 'top-margin',
            }
        })
        new_qg_data['questions'] = questions
        data = self.update_config_data(path=new_qg_path, updated=new_qg_data, **data)
        return data

    def add_question_tech_agronomic_tillage(self, **data) -> dict:
        # Create key and values
        q_keyword = 'tech_agronomic_tillage'
        self.create_new_question(
            keyword=q_keyword,
            translation={
                'label': {
                    'en': 'A3: Differentiate tillage systems'
                }
            },
            question_type='select',
            values=[
                self.create_new_value(
                    keyword='tillage_no',
                    translation={
                        'label': {
                            'en': 'A 3.1: No tillage'
                        }
                    },
                    order_value=1,
                ),
                self.create_new_value(
                    keyword='tillage_reduced',
                    translation={
                        'label': {
                            'en': 'A 3.2: Reduced tillage (> 30% soil cover)'
                        }
                    },
                    order_value=2,
                ),
                self.create_new_value(
                    keyword='tillage_full',
                    translation={
                        'label': {
                            'en': 'A 3.3: Full tillage (< 30% soil cover)'
                        }
                    },
                    order_value=3,
                ),
            ]
        )

        # Prepare configuration (with condition)
        question_configuration = {
            'keyword': q_keyword,
            'form_options': {
                'question_condition': q_keyword
            }
        }

        qg_path = (
            'section_specifications', 'tech__3', 'tech__3__6', 'tech_qg_21')
        qg_data = self.find_in_data(path=qg_path, **data)

        # Add question
        qg_data['questions'] = qg_data['questions'] + [
            question_configuration]

        # Add condition to the first question
        new_condition = f"=='measures_agronomic_a3'|{q_keyword}"
        question_conditions = qg_data['questions'][0]['form_options'].get(
            'question_conditions', [])
        question_conditions.append(new_condition)
        qg_data['questions'][0]['form_options'][
            'question_conditions'] = question_conditions

        data = self.update_config_data(path=qg_path, updated=qg_data, **data)

        # Update summary options of the main question (checkbox about SLM
        # measures).
        q_path = (
            'section_specifications', 'tech__3', 'tech__3__6', 'tech_qg_8',
            'tech_measures')
        q_data = self.find_in_data(path=q_path, **data)

        q_data['summary'] = {
            'types': ['full'],
            'default': {
                'field_name': 'classification_measures',
                'get_value': {
                    # Use a new getter which includes the subquestions
                    'name': 'get_classification_measures'
                }
            }
        }

        data = self.update_config_data(path=q_path, updated=q_data, **data)

        return data

    def rename_option_a6_others(self, **data) -> dict:
        self.update_translation(
            update_pk=1516,
            **{
                'label': {
                    'en': 'A7: Others'
                }
            }
        )
        return data

    def add_option_a6_residue_management(self, **data) -> dict:
        self.add_new_value(
            question_keyword='tech_measures_agronomic_sub',
            value=self.create_new_value(
                keyword='measures_agronomic_a6_residue_management',
                translation={
                    'label': {
                        'en': 'A6: Residue management'
                    }
                },
                order_value=6,
            ),
            order_value=6,
        )
        return data

    def add_other_degradation_textfield(self, **data) -> dict:
        q_keyword = 'tech_degradation_other'
        self.create_new_question(
            keyword=q_keyword,
            translation=1018,
            question_type='text'
        )

        subcat_path = ('section_specifications', 'tech__3', 'tech__3__7')

        # Questiongroup exists already, but with stub question. Replace this
        # question and add the condition.
        qg_path = subcat_path + ('tech_qg_231', )
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['questions'] = [{
            'keyword': q_keyword
        }]
        qg_data['form_options'] = {
            'questiongroup_condition': 'tech_qg_231'
        }
        qg_data['view_options'] = {
            'conditional_question': 'degradation_other'
        }
        data = self.update_config_data(path=qg_path, updated=qg_data, **data)

        # Add conditions
        condition = "=='degradation_other'|tech_qg_231"
        subcat_data = self.find_in_data(path=subcat_path, **data)
        subcat_data['form_options']['questiongroup_conditions'] += [condition]
        subcat_data['questiongroups'][0]['questions'][0]['form_options']['questiongroup_conditions'] += [
            condition
        ]
        data = self.update_config_data(path=subcat_path, updated=subcat_data, **data)

        return data

    def add_other_measures_textfield(self, **data) -> dict:
        q_keyword = 'tech_measures_other'
        self.create_new_question(
            keyword=q_keyword,
            translation=1018,
            question_type='text'
        )

        subcat_path = ('section_specifications', 'tech__3', 'tech__3__6')

        # Questiongroup exists already, but with stub question. Replace this
        # question and add the condition.
        qg_path = subcat_path + ('tech_qg_25', )
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['questions'] = [{
            'keyword': q_keyword
        }]
        qg_data['form_options'] = {
            'questiongroup_condition': 'tech_qg_25'
        }
        qg_data['view_options'] = {
            'conditional_question': 'tech_measures_indirect'
        }
        data = self.update_config_data(path=qg_path, updated=qg_data, **data)

        # Add conditions
        condition = "=='tech_measures_indirect'|tech_qg_25"
        subcat_data = self.find_in_data(path=subcat_path, **data)
        subcat_data['form_options']['questiongroup_conditions'] += [condition]
        subcat_data['questiongroups'][0]['questions'][0]['form_options']['questiongroup_conditions'] += [
            condition
        ]
        data = self.update_config_data(path=subcat_path, updated=subcat_data, **data)

        return data

    def add_question_tech_residue_management(self, **data) -> dict:
        # Create key and values
        q_keyword = 'tech_residue_management'
        self.create_new_question(
            keyword=q_keyword,
            translation={
                'label': {
                    'en': 'A6: Specify residue management'  # If this text changes, also adapt the release notes above
                }
            },
            question_type='select',
            values=[
                self.create_new_value(
                    keyword='residue_management_burned',
                    translation={
                        'label': {
                            'en': 'A 6.1: burned'
                        }
                    },
                    order_value=1,
                ),
                self.create_new_value(
                    keyword='residue_management_grazed',
                    translation={
                        'label': {
                            'en': 'A 6.2: grazed'
                        }
                    },
                    order_value=2,
                ),
                self.create_new_value(
                    keyword='residue_management_collected',
                    translation={
                        'label': {
                            'en': 'A 6.3: collected'
                        }
                    },
                    order_value=3,
                ),
                self.create_new_value(
                    keyword='residue_management_retained',
                    translation={
                        'label': {
                            'en': 'A 6.4: retained'
                        }
                    },
                    order_value=4,
                ),
            ]
        )

        # Prepare configuration (with condition)
        question_configuration = {
            'keyword': q_keyword,
            'form_options': {
                'question_condition': q_keyword
            }
        }

        qg_path = (
            'section_specifications', 'tech__3', 'tech__3__6', 'tech_qg_21')
        qg_data = self.find_in_data(path=qg_path, **data)

        # Add question
        qg_data['questions'] = qg_data['questions'] + [
            question_configuration]

        # Add condition to the first question
        new_condition = f"=='measures_agronomic_a6_residue_management'|{q_keyword}"
        question_conditions = qg_data['questions'][0]['form_options'].get(
            'question_conditions', [])
        question_conditions.append(new_condition)
        qg_data['questions'][0]['form_options'][
            'question_conditions'] = question_conditions

        data = self.update_config_data(path=qg_path, updated=qg_data, **data)
        return data

    def remove_subcategory_1_6(self, **data) -> dict:
        cat_path = ('section_general_information', 'tech__1')
        cat_data = self.find_in_data(path=cat_path, **data)
        cat_data['subcategories'] = [
            subcat for subcat in cat_data['subcategories']
            if subcat['keyword'] != 'tech__1__6'
        ]
        data = self.update_config_data(path=cat_path, updated=cat_data, **data)
        return data

    def remove_person_address_questions(self, **data) -> dict:
        qg_path = (
            'section_general_information', 'tech__1', 'tech__1__2',
            'tech_qg_184')
        remove_questions = [
            'person_address',
            'person_phone_1',
            'person_phone_2',
            'person_email_1',
            'person_email_2',
        ]
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['questions'] = [
            q for q in qg_data['questions']
            if q['keyword'] not in remove_questions]
        # Also update the view template
        qg_data['view_options']['template'] = 'select_user_2018'
        data = self.update_config_data(path=qg_path, updated=qg_data, **data)
        return data

    def delete_person_address_data(self, **data) -> dict:
        delete_questions = [
            'person_address',
            'person_phone_1',
            'person_phone_2',
            'person_email_1',
            'person_email_2',
        ]
        for question in delete_questions:
            data = self.update_data('tech_qg_184', question, None, **data)
        return data

    def move_date_documentation_data(self, **data) -> dict:

        moved_date = None
        if 'qg_accept_conditions' in data:
            # Can only be 1 entry
            moved_date = data['qg_accept_conditions'][0].get('date_documentation')

        if moved_date:
            del data['qg_accept_conditions'][0]['date_documentation']
            data['tech_qg_250'] = [{'date_documentation': moved_date}]

        return data

    def move_date_documentation(self, **data) -> dict:

        # Remove from 1.3
        qg_path = (
            'section_general_information', 'tech__1', 'tech__1__3',
            'qg_accept_conditions')
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['questions'] = [
            q for q in qg_data['questions']
            if q['keyword'] != 'date_documentation'
        ]
        data = self.update_config_data(path=qg_path, updated=qg_data, **data)

        # Add to 7.1 (create a new questiongroup)
        qg_keyword = 'tech_qg_250'
        self.create_new_questiongroup(
            keyword=qg_keyword,
            translation=None
        )
        # Also create a new question (comments)
        comments_key = 'tech_date_comments'
        self.create_new_question(
            keyword=comments_key,
            translation=5004,
            question_type='text'
        )
        subcat_path = ('section_specifications', 'tech__7', 'tech__7__1')
        subcat_data = self.find_in_data(path=subcat_path, **data)
        subcat_data['questiongroups'] = subcat_data['questiongroups'] + [{
            'keyword': qg_keyword,
            'questions': [
                {
                    'keyword': 'date_documentation'
                },
                {
                    'keyword': comments_key
                }
            ]
        }]
        data = self.update_config_data(
            path=subcat_path, updated=subcat_data, **data)

        return data

    def add_option_user_resourceperson_type(self, **data) -> dict:
        self.add_new_value(
            question_keyword='user_resourceperson_type',
            value=self.create_new_value(
                keyword='resourceperson_cocompiler',
                translation={
                    'label': {
                        'en': 'co-compiler'
                    }
                },
                order_value=3,
                configuration_editions=self.all_configuration_editions
            ),
        )
        return data

    def rename_tech_individuals(self, **data) -> dict:
        # Add option to show helptext as tooltip. Then add tooltip.
        qg_path = (
            'section_specifications', 'tech__5', 'tech__5__6', 'tech_qg_71')
        qg_data = self.find_in_data(path=qg_path, **data)
        questions = []
        for question in qg_data['questions']:
            if question['keyword'] == 'tech_individuals':
                question['form_options'] = {'helptext_position': 'tooltip'}
            questions.append(question)
        qg_data['questions'] = questions
        data = self.update_config_data(path=qg_path, updated=qg_data, **data)
        self.update_translation(
            update_pk=1139,
            **{
                'label': {
                    'en': 'Individuals or groups'
                },
                'helptext': {
                    'en': 'Indicate if land users apply the technology as individuals or as members of a specific group/ company.'
                }
            }
        )
        return data

    def rename_tech_input_maint_total_estimation(self, **data) -> dict:
        self.update_translation(
            update_pk=1321,
            **{
                'label': {
                    'en': 'If you are unable to break down the costs in the table above, give an estimation of the total costs of maintaining the Technology'
                }
            }
        )
        return data

    def move_tech_input_maint_total_estimation(self, **data) -> dict:
        qg_path = (
            'section_specifications', 'tech__4', 'tech__4__7', 'tech_qg_50')
        qg_data = self.find_in_data(path=qg_path, **data)
        del qg_data['form_options']
        del qg_data['view_options']
        data = self.update_config_data(path=qg_path, updated=qg_data, **data)
        return data

    def rename_tech_input_est_total_estimation(self, **data) -> dict:
        self.update_translation(
            update_pk=1319,
            **{
                'label': {
                    'en': 'If you are unable to break down the costs in the table above, give an estimation of the total costs of establishing the Technology'
                }
            }
        )
        return data

    def move_tech_input_est_total_estimation(self, **data) -> dict:
        qg_path = (
            'section_specifications', 'tech__4', 'tech__4__5', 'tech_qg_42')
        qg_data = self.find_in_data(path=qg_path, **data)
        del qg_data['form_options']
        del qg_data['view_options']
        data = self.update_config_data(path=qg_path, updated=qg_data, **data)
        return data

    def remove_tech_maint_type(self, **data) -> dict:
        qg_path = (
            'section_specifications', 'tech__4', 'tech__4__6', 'tech_qg_43')
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['questions'] = [
            q for q in qg_data['questions'] if q['keyword'] != 'tech_maint_type']
        data = self.update_config_data(path=qg_path, updated=qg_data, **data)
        return data

    def delete_tech_maint_type(self, **data) -> dict:
        return self.update_data('tech_qg_43', 'tech_maint_type', None, **data)

    def remove_tech_est_type(self, **data) -> dict:
        qg_path = (
            'section_specifications', 'tech__4', 'tech__4__4', 'tech_qg_165')
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['questions'] = [
            q for q in qg_data['questions'] if q['keyword'] != 'tech_est_type']
        data = self.update_config_data(path=qg_path, updated=qg_data, **data)
        return data

    def delete_tech_est_type(self, **data: dict) -> dict:
        return self.update_data('tech_qg_165', 'tech_est_type', None, **data)

    def add_option_tech_lu_grazingland_transhumant(self, **data) -> dict:
        self.add_new_value(
            question_keyword='tech_lu_grazingland_extensive',
            value=self.create_new_value(
                keyword='lu_grazingland_transhumant',
                translation={
                    'label': {
                        'en': 'Transhumant pastoralism'
                    },
                    'helptext': {
                        'en': '<strong>Transhumant pastoralism/ transhumance</strong>: regular movements of herds between fixed areas in order to benefit from the seasonal variability of climates and pastures.'
                    }
                },
                order_value=4
            ),
        )

        # Also rename question about extensive grazing
        self.update_translation(
            update_pk=1238,
            **{
                "label": {
                    "en": "Extensive grazing"
                },
                "helptext": {
                    "en": "<strong>Ge: Extensive grazing</strong>: grazing on natural or semi-natural grasslands, grasslands with trees/ shrubs (savannah vegetation) or open woodlands for livestock and wildlife."
                }
            }
        )

        return data

    def rename_tech_lu_grazingland_pastoralism(self, **data) -> dict:
        self.update_translation(
            update_pk=1759,
            **{
                'label': {
                    'en': 'Semi-nomadic pastoralism'
                },
                'helptext': {
                    'en': '<strong>Semi-nomadic pastoralism</strong>: animal owners have a permanent place of residence or without cultivation practiced. Herds are moved to distant grazing grounds.'
                }
            }
        )
        return data

    def rename_us_dollars(self, **data) -> dict:
        self.update_translation(
            update_pk=1904,
            **{
                "label": {
                    "en": "USD"
                }
            }
        )
        return data

    def reformat_agroclimatic_zone(self, **data) -> dict:
        qg_path = (
            'section_specifications', 'tech__5', 'tech__5__1', 'tech_qg_55')
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['form_options']['template'] = 'default'
        qg_data['questions'][1]['form_options']['label_columns_class'] = 'top-margin'
        data = self.update_config_data(path=qg_path, updated=qg_data, **data)

        # Also update translations
        self.update_translation(
            update_pk=2219,
            **{
                "label": {
                    "en": "Agro-climatic zone"
                },
                "helptext": {
                    "en": "<p>The length of growing period (LGP) is defined as the period when precipitation is more than half of the potential evapotranspiration (PET) and the temperature is higher than 6.5° C.</p><p>Tick max. 1 answer.</p>"
                }
            }
        )
        self.update_translation(
            update_pk=1073,
            **{
                "label": {
                    "en": "Specifications/ comments on climate"
                },
                "helptext": {
                    "en": "E.g. mean annual temperature"
                }
            }
        )

        return data

    def add_general_comments_field(self, **data) -> dict:

        cat_path = ('section_specifications', 'tech__7')
        cat_data = self.find_in_data(path=cat_path, **data)

        subcat_keyword = 'tech__7__4'
        self.create_new_category(
            keyword=subcat_keyword,
            translation={
                'label': {
                    'en': 'General comments'
                }
            }
        )
        qg_keyword = 'tech_qg_253'
        self.create_new_questiongroup(
            keyword=qg_keyword,
            translation=None
        )
        q_keyword = 'tech_general_comments'
        self.create_new_question(
            keyword=q_keyword,
            translation={
                'label': {
                    'en': 'General comments'
                },
                'helptext': {
                    'en': 'Feedback regarding the questionnaire, the database or general remarks.'
                }
            },
            question_type='text'
        )

        cat_data['subcategories'] += [{
            'keyword': subcat_keyword,
            'form_options': {
                'numbering': '7.4'
            },
            'questiongroups': [
                {
                    'keyword': qg_keyword,
                    'questions': [
                        {
                            'keyword': q_keyword,
                            'form_options': {
                                'template': 'no_label'
                            },
                            'view_options': {
                                'label_position': 'none'
                            }
                        }
                    ]
                }
            ]
        }]
        return self.update_config_data(path=cat_path, updated=cat_data, **data)

    def various_translation_updates(self, **data) -> dict:
        self.update_translation(
            update_pk=1939,
            **{
                "label": {
                    "en": "per Technology area"
                },
                "helptext": {
                    "en": "e.g. area of terraced cropland, area closed for natural regeneration, area used for rotational grazing, etc."
                }
            }
        )
        self.update_translation(
            update_pk=2786,
            **{
                "label": {
                    "en": "Detailed description of the Technology"
                },
                "helptext": {
                    "en": "<p>The detailed description should provide a concise but comprehensive picture of the Technology to outsiders. It should therefore address key questions such as:</p><ol><li>Where is the Technology applied (natural and human environment)?</li><li>What are the main characteristics/ elements of the Technology (including technical specifications)?</li><li>What are the purposes/ functions of the Technology?</li><li>What major activities/ inputs are needed to establish/ maintain the Technology?</li><li>What are the benefits/ impacts of the Technology?</li><li>What do land users like / dislike about the Technology?</ol><p>The description should ideally be 2,500-3,000 characters in length; the absolute maximum is 3,500 characters. Additional, more detailed descriptions may be uploaded to the database as separate documents.</p><p>First, the land user(s) should describe the Technology without going into detail. The compiler then complements the description, integrating as much information as possible from the completed questionnaire.</p>"
                }
            }
        )
        self.update_translation(
            update_pk=2725,
            **{
                "label": {
                    "en": "Photos of the Technology"
                },
                "helptext": {
                    "en": "<ul><li>Provide photos showing an overview and details of the Technology.</li><li>Provide at least two digital files (JPG, PNG, GIF), i.e. files from a digital camera, or scans from prints, negative films or slide films.</li><li>Maximum file size: 3 MB.</li><li>Photos should be of high quality/ high resolution and not manipulated or distorted.</li><li>An explanation (description) is required for each photo submitted! Photos should match the description given in 2.2 and help illustrate the technical drawing in 4.1.</li><li>Where appropriate, photos should depict the situation before and after or with and without SLM measures.</li><li>Good photos are crucial for understanding and illustrating the main features of the Technology.</li><li>The first photo you upload will be set as title photo in the database and front page photo in the printable summary. The orientation should be landscape.</li><li>The second and third photos uploaded will appear on page 2 on the printable summary. These two photos will be cropped automatically to a square format.</li><li>For ideal display in the summary you can crop the photos (before uploading) as follows: Photo 1 should have a panorama format (height to width 1:2), while photos 2 and 3 should ideally be square (height to width 1:1).</li><li>You can upload further photos for display in the database, but not in the summary.</li></ul><p><strong>Example:</strong></p><div class=\"row\"><div class=\"medium-6 columns\"><img src=\"/static/assets/img/smallmedium_QTKEN05_1.jpg\"><p class=\"form-example-legend\"><strong>Overview</strong>: Fanya juu terraces with grass strips on the risers developed into bench terraces (Photo: Machakos, Kenya)</p></div><div class=\"medium-6 columns\"><img src=\"/static/assets/img/mediumsmall_QaKEN01_2.jpg\"><p class=\"form-example-legend\"><strong>Detail</strong>: Fanya juu bund in a maize field after harvest: Napier grass on the upper part of the bund, and maize residues in the ditch below. (Photo: H.P. Liniger)</p></div></div>"
                }
            }
        )
        self.update_translation(
            update_pk=2802,
            **{
                "label": {
                    "en": "Strengths/ advantages/ opportunities of the Technology"
                },
                "helptext": {
                    "en": "Give a concluding statement about the Technology. One statement only per text field. Differentiate between the perspectives of land users and key resource persons."
                }
            }
        )
        self.update_translation(
            update_pk=2754,
            **{
                "label": {
                    "en": "Reference to Questionnaire(s) on SLM Approaches (documented using WOCAT)"
                },
                "helptext": {
                    "en": "To understand properly the implementation of the Technology, the associated SLM Approach must be described. Use the search field to find the SLM Approach in the database."
                }
            }
        )
        self.update_translation(
            update_pk=2806,
            **{
                "label": {
                    "en": "Main purpose(s) of the Technology"
                },
                "helptext": {
                    "en": "Tick max. 5 answers"
                }
            }
        )
        self.update_translation(
            update_pk=1543,
            **{
                "label": {
                    "en": "Wg: gully erosion/ gullying"
                },
                "helptext": {
                    "en": "<strong>Gully erosion/ gullying</strong>: Removal of soil along drainage lines by surface runoff, creating deep channels (more than 30 cm deep)"
                }
            }
        )
        self.update_translation(
            update_pk=1544,
            **{
                "label": {
                    "en": "Wm: mass movements/ landslides"
                },
                "helptext": {
                    "en": "<strong>Mass movements/ landslides</strong>: the downward falling or sliding of a mass of earth, debris, or rock on a slope (includes mudflows and rockfalls); also called landslip."
                }
            }
        )
        self.update_translation(
            update_pk=1545,
            **{
                "label": {
                    "en": "Wr: riverbank erosion"
                },
                "helptext": {
                    "en": "<strong>Riverbank erosion</strong>: the wearing away of the banks of a stream or river"
                }
            }
        )
        self.update_translation(
            update_pk=1546,
            **{
                "label": {
                    "en": "Wc: coastal erosion"
                },
                "helptext": {
                    "en": "<strong>Coastal erosion</strong>: Loss or displacement of land along the coastline due to the action of waves, currents or tides, leading to landward retreat of the shoreline"
                }
            }
        )
        self.update_translation(
            update_pk=1558,
            **{
                "label": {
                    "en": "Ps: subsidence of organic soils, settling of soil"
                },
                "helptext": {
                    "en": "<strong>Subsidence of organic soils, settling of soils</strong>: downward motion of soil surface, e.g. due to drainage of organic soils"
                }
            }
        )
        self.update_translation(
            update_pk=2726,
            **{
                "label": {
                    "en": "Prevention, reduction, or restoration of land degradation"
                },
                "helptext": {
                    "en": "Tick max. two answers. If you tick «not applicable», please tick no other answer."
                }
            }
        )
        self.update_translation(
            update_pk=2790,
            **{
                "label": {
                    "en": "Technical drawing of the Technology"
                },
                "helptext": {
                    "en": "<p>Please provide a comprehensive and detailed drawing (including dimensions) of the Technology and indicate technical specifications, measurements, spacing, gradient, etc. You can also provide several drawings showing (a) a temporal sequence of operations or (b) different elements or details of the Technology. Alternatively you can also provide one or several photographs with technical specifications drawn and/ or written onto the photograph(s). Include as much technical information as possible on the drawings (or photographs).</p><p>Keep the drawing simple and schematic. The technical drawing is crucial for understanding the Technology! Scan the drawing and upload the scan.</p><ul><li>Supported file types: PDF, JPG, PNG, maximum file size: 3 MB.</li><li>Technical drawings should not be extreme landscape or portrait formats. Square format is ideal.</li><li>The first three uploaded technical drawings will appear in the summary</li><li>Technical drawings should contain no text in questionnaires that are being translated into other languages. In this case, the drawing should contain only symbols and/or numbers. Any text accompanying the drawing should be entered into the next field, where it can be translated.</li></ul><p><strong>Example</strong>: Technical drawing indicating technical specifications, dimensions, spacing<br><img src=\"/static/assets/img/qt_technical_drawing.jpg\"></img></p>"
                }
            }
        )
        self.update_translation(
            update_pk=1247,
            **{
                "label": {
                    "en": "If using a local area unit, indicate conversion factor to one hectare (e.g. 1 ha = 2.47 acres): 1 ha ="
                },
                "helptext": {
                    "en": "Refer to area specified in 2.5<br>For conversions between local and metric units we recommend using an online unit converter, e.g. http://www.unitconverters.net/"
                }
            }
        )
        # Update configuration: show helptext as tooltip and change column size.
        qg_path = ('section_specifications', 'tech__4', 'tech__4__3',
                   'tech_qg_163')
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['form_options']['columns_custom'] = [["4", "8"]]
        for q_data in qg_data['questions']:
            if q_data['keyword'] == 'tech_area_unit_conversion':
                q_data['form_options'] = {
                    'helptext_position': 'tooltip'
                }
        data = self.update_config_data(path=qg_path, updated=qg_data, **data)

        self.update_translation(
            update_pk=1283,
            **{
                "label": {
                    "en": "Specify dimensions of unit (if relevant)"
                },
                "helptext": {
                    "en": "<strong>Example:</strong> stone lines: 250 m, dam: 20’000 m<sup>3</sup>"
                }
            }
        )
        self.update_translation(
            update_pk=1317,
            **{
                "label": {
                    "en": "If relevant, indicate exchange rate from USD to local currency (e.g. 1 USD = 79.9 Brazilian Real): 1 USD ="
                }
            }
        )
        self.update_translation(
            update_pk=1039,
            **{
                "label": {
                    "en": "Timing (season)"
                },
                "helptext": {
                    "en": "<p><strong>Timing</strong>: Time during which activity is carried out, e.g. month or season, or \"after harvest of crops\", \"before onset of rains\", etc.</p>"
                }
            }
        )
        self.update_translation(
            update_pk=2355,
            **{
                "label": {
                    "en": "Labour"
                },
                "helptext": {
                    "en": "<strong>Labour</strong> includes total person-days, be they paid or unpaid (e.g. non-hired family labour). For “Costs per Unit” indicate daily wage for hired labour. If relevant, differentiate between skilled and unskilled labour."
                }
            }
        )
        self.update_translation(
            update_pk=1042,
            **{
                "label": {
                    "en": "% of costs borne by land users"
                },
                "helptext": {
                    "en": "<p>The percentage of costs that land users contribute. Specify for each input. E.g. If they receive fertilizer for free from a supporting agency, indicate fertilizer = 0%; if land users provide all labour force, without receiving any reward or subsidies, indicate labour = 100%.</p><p>For inputs which are fully paid or provided by external entities: always enter 0%</p>"
                }
            }
        )
        self.update_translation(
            update_pk=2917,
            **{
                "label": {
                    "en": "Natural and human environment"
                },
                "helptext": {
                    "en": "<p>Give details of the natural (biophysical) conditions where the Technology is applied. Make specific reference to the sites where the documented Technology has been assessed and analysed. Tick one box per question only, except for annual rainfall, slope and soil parameters (see indications below). Use comment sections to specify your answers and provide additional information.</p><p><strong>Note:</strong> Some of the environmental conditions (e.g. slope angle, soil characteristics, water quality/ availability, etc.) may change as a result of the Technology! However, you are requested to <strong>describe the conditions as they were without any impact of sustainable land management!</strong></p><p>In exceptional cases, certain questions might not be relevant for the Technology. In such cases, skip the question but use the comment sections to explain why you are skipping it.</p>"
                }
            }
        )
        self.update_translation(
            update_pk=2717,
            **{
                "label": {
                    "en": "Topography"
                },
                "helptext": {
                    "en": "Tick max. 2 answers per question."
                }
            }
        )
        self.update_translation(
            update_pk=2718,
            **{
                "label": {
                    "en": "Soils"
                },
                "helptext": {
                    "en": "<p>The following parameters are based on FAO standards.</p><p>Tick max. 2 answers per question.</p>"
                }
            }
        )
        self.update_translation(
            update_pk=1098,
            **{
                "label": {
                    "en": "Soil depth on average"
                },
                "helptext": {
                    "en": "<strong>Soil depth</strong>: distance from top to parent material."
                }
            }
        )
        # Update Helptext positioning
        q_path = ('section_specifications', 'tech__5', 'tech__5__3',
                  'tech_qg_58', 'tech_soil_depth')
        q_data = self.find_in_data(path=q_path, **data)
        q_data['form_options'] = {
            'helptext_position': 'tooltip'
        }
        data = self.update_config_data(path=q_path, updated=q_data, **data)

        self.update_translation(
            update_pk=1709,
            **{
                "label": {
                    "en": "mixed (subsistence/ commercial)"
                }
            }
        )
        self.update_translation(
            update_pk=2795,
            **{
                "label": {
                    "en": "Average area of land used by land users applying the Technology"
                },
                "helptext": {
                    "en": "Indicate the total area owned or leased by land users, including the land where no Technology is applied. Tick max. two answers."
                }
            }
        )
        self.update_translation(
            update_pk=2798,
            **{
                "label": {
                    "en": "On-site impacts the Technology has shown"
                },
                "helptext": {
                    "en": "<p>First, tick relevant impacts (tick boxes on the left). Then for each selected impact, tick the extent as follows.</p><ul><li><strong>-3</strong>: Very negative impact (- 50-100%)</li><li><strong>-2</strong>: Negative impact (- 20-50%)</li><li><strong>-1</strong>: Slightly negative impact (- 5-20%)</li><li><strong>0</strong>: Negligible impact</li><li><strong>1</strong>: Slightly positive impact (+5-20%)</li><li><strong>2</strong>: Positive impact (+20-50%)</li><li><strong>3</strong>: Very positive impact (+50-100%)</li></ul><p>Quantify impacts (if possible) and add comments / specifications.</p><p><strong>Caution</strong>: If you don’t tick the relevant impacts, your specifications (on the right hand side) will not be saved.</p>"
                }
            }
        )
        self.update_translation(
            update_pk=2244,
            **{
                "label": {
                    "en": "production area"
                },
                "helptext": {
                    "en": "Land under cultivation/ use"
                }
            }
        )
        self.update_translation(
            update_pk=2246,
            **{
                "label": {
                    "en": "energy generation"
                },
                "helptext": {
                    "en": "E.g. hydro, biogas"
                }
            }
        )
        self.update_translation(
            update_pk=1302,
            **{
                "label": {
                    "en": "increase or decrease"
                }
            }
        )
        self.update_translation(
            update_pk=2799,
            **{
                "label": {
                    "en": "Exposure and sensitivity of the Technology to gradual climate change and climate-related extremes/ disasters (as perceived by land users)"
                },
                "helptext": {
                    "en": "<p>Indicate gradual changes in climate and climate-related extremes as observed by land users in the last 10 years (trend). Note: for a more detailed assessment, fill in questionnaire module on climate change adaptation.</p><p>Tick all gradual changes in climate and climate-related extremes/ disasters to which the Technology is exposed</p><p>Source: Disaster Category Classification and Peril Terminology for Operational Purposes. CRED and Munich RE. 2009. Working Paper. Adapted by WOCAT.</p>"
                }
            }
        )
        self.update_translation(
            update_pk=1933,
            **{
                "label": {
                    "en": "11-50%"
                }
            }
        )
        self.update_translation(
            update_pk=1934,
            **{
                "label": {
                    "en": "51-90%"
                }
            }
        )
        self.update_translation(
            update_pk=1935,
            **{
                "label": {
                    "en": "91-100%"
                }
            }
        )
        self.update_translation(
            update_pk=1842,
            **{
                "label": {
                    "en": "11-50%"
                }
            }
        )
        self.update_translation(
            update_pk=1843,
            **{
                "label": {
                    "en": "> 50%"
                }
            }
        )
        self.update_translation(
            update_pk=1335,
            **{
                "label": {
                    "en": "Of all those who have adopted the Technology, how many did so spontaneously, i.e. without receiving any material incentives/ payments?"
                }
            }
        )
        self.update_translation(
            update_pk=2805,
            **{
                "label": {
                    "en": "Links to relevant online information"
                }
            }
        )
        self.update_translation(
            update_pk=1334,
            **{
                "label": {
                    "en": "Specify assessment of off-site impacts (measurements)"
                }
            }
        )

        return data

    def add_new_LUT_listvalues(self, **data) -> dict:

        # Add annual cropping list of crops, Perennial cropping list of crops, Tree and shrub cropping list of crops
        annual_crops_keyword = 'tech_lu_cropland_annual_cropping_crops'
        perennial_crops_keyword = 'tech_lu_cropland_perennial_cropping_crops'
        treeshrub_crops_keyword = 'tech_lu_cropland_tree_shrub_cropping_crops'

        # Add animal types, Add new products and services
        type_animal_keyword = 'tech_lu_grazingland_animals'
        type_products_keyword = 'tech_lu_grazingland_products'

        # Add new forest plantation type, Add new tree types
        type_forest_plantation_keyword = 'tech_lu_forest_plantation_type'
        type_tree_keyword = 'tech_lu_forest_tree_type'

        # Dictionary of values to be added
        [
            self.add_new_value(
                question_keyword=qk,
                value=self.create_new_value(
                    keyword=k,
                    translation={
                        'label': {
                            'en': l
                        }
                    },
                ),
            )
            for i, (qk, k, l) in enumerate([
                (annual_crops_keyword, 'annual_crops_450', 'cereals - buckwheat'),
                (annual_crops_keyword, 'annual_crops_458', 'legumes and pulses - lentils'),
                (annual_crops_keyword, 'annual_crops_472', 'root/tuber crops - yams, taro/cocoyam, other'),
                (perennial_crops_keyword, 'perennial_crops_529', 'passiflora - passion fruit, maracuja'),
                # (perennial_crops_keyword, 'perennial_crops_465', 'pineapple'), # pineapple is already present
                (perennial_crops_keyword, 'perennial_crops_474', 'herbs, chili, capsicum'),
                (perennial_crops_keyword, 'perennial_crops_427', 'fodder crops - grasses'),
                (perennial_crops_keyword, 'perennial_crops_418', 'fodder crops - legumes, clover'),
                (perennial_crops_keyword, 'perennial_crops_non_fodder', 'non-fodder grasses - e.g. for thatching or stabilization (vetiver)'),
                (perennial_crops_keyword, 'perennial_crops_natural_grasses', 'natural grasses'),
                (treeshrub_crops_keyword, 'tree_shrub_474', 'cactus, cactus-like (e.g. opuntia)'),
                (treeshrub_crops_keyword, 'tree_shrub_cork_oak', 'cork oak'),
                (treeshrub_crops_keyword, 'tree_shrub_caragana', 'caragana'),
                (treeshrub_crops_keyword, 'tree_shrub_argan', 'argan'),

                (type_animal_keyword, 'animals_cattle', 'cattle - dairy and beef (e.g. zebu)'),
                (type_animal_keyword, 'animals_beekeeping', 'beekeeping, apiculture'),
                (type_animal_keyword, 'animals_fish', 'fish'),
                (type_products_keyword, 'prod_service_manure', 'manure as fertilizer/ energy production'),
                (type_products_keyword, 'prod_service_economic', 'economic security, investment prestige'),

                (type_forest_plantation_keyword, 'plantation_forest_shrubland', 'subtropical shrubland plantation'),
                (type_tree_keyword, 'tree_type_acer', 'Acer species (e.g. maple)'),
                (type_tree_keyword, 'tree_type_cedrus', 'Cedrus species'),
                (type_tree_keyword, 'tree_type_erythrina', 'Erythrina species'),
                (type_tree_keyword, 'tree_type_salix', 'Salix species'),
                (type_tree_keyword, 'tree_type_haloxylon', 'Haloxylon species'),
            ])
        ]

        # Add new livestock species population
        # This is added after adding the new Livestock animals
        #  - same keyword is used to ensure population is matched to species
        keyword_species = 'tech_lu_grazingland_pop_species'

        [
            self.add_new_value(
                question_keyword=qk,
                value=self.get_value(
                    keyword=k,
                ),
            )
            for i, (qk, k) in enumerate([
                (keyword_species, 'animals_cattle'),
                (keyword_species, 'animals_beekeeping'),
                (keyword_species, 'animals_fish'),
            ])
        ]

        return data

    def do_nothing(self, **data) -> dict:
        return data

    def _create_land_use_subquestions(
            self, qg_path: tuple, keyword: str, label: str, values_list: list,
            other_label: str, conditional_value: str or None,
            question_condition_keyword: str or None=None,
            label_view: str or None=None, **data) -> dict:

        if question_condition_keyword is None:
            question_condition_keyword = keyword

        # Create question
        label_view = label_view or label
        self.create_new_question(
            keyword=keyword,
            translation={
                'label': {
                    'en': label
                },
                'label_view': {
                    'en': label_view,
                }
            },
            question_type='multi_select',
            values=self.create_new_values_list(values_list),
        )
        question_configuration = {
            'keyword': keyword,
            'form_options': {
                'question_condition': question_condition_keyword,
                'row_class': 'top-margin'
            }
        }

        # Create "other" question
        other_keyword = f'{keyword}_other'
        self.create_new_question(
            keyword=other_keyword,
            translation={
                'label': {
                    'en': other_label
                }
            },
            question_type='char'
        )
        other_configuration = {
            'keyword': other_keyword,
            'form_options': {
                'question_condition': question_condition_keyword,
                'template': 'checkbox_other',
                'label_position': 'placeholder',
                'label_class': 'input-full-width'
            },
            'view_options': {
                'template': 'checkbox_other',
            }
        }

        # Add configuration
        qg_data = self.find_in_data(path=qg_path, **data)
        qg_data['questions'] = qg_data['questions'] + [
            question_configuration, other_configuration]
        if conditional_value:
            new_condition = f"=='{conditional_value}'|{keyword}"
            question_conditions = qg_data['questions'][0]['form_options'].get(
                'question_conditions', [])
            question_conditions += [new_condition]
            qg_data['questions'][0]['form_options'][
                'question_conditions'] = question_conditions

        return self.update_config_data(path=qg_path, updated=qg_data, **data)
