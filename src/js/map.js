(function ($) {
    $.fn.bindMapActions = function(options) {

        var defaults = {
            inModal: false,
            editable: true
        };
        var settings = $.extend({}, defaults, options);

        // Map settings
        var dataProjection = 'EPSG:4326',
            featureProjection = 'EPSG:3857',
            geomFormat = new ol.format.GeoJSON({
                defaultDataProjection: dataProjection
            });

        // Elements
        var qgContainer = this,
            mapPanel = qgContainer.find('.map-form-container').first(),
            mapContainer = mapPanel.closest('.map-container');

        if (settings.inModal) {
            // If the map is opened in a modal, we need to update the size of
            // the map panel after the map is created.
            var newHeight = qgContainer.height() - 50;
            mapPanel.height(newHeight);
            $('.map-overlay').height(newHeight - 32);
            $('.map-controls').height(newHeight);
        }

        // Styles
        var defaultStyle = getDefaultVectorStyle(),
            selectStyle = getSelectVectorStyle(),
            deleteStyle = getDeleteVectorStyle();

        // Layers
        var vectorSource = new ol.source.Vector(),
            vectorLayer = new ol.layer.Vector({
                source: vectorSource,
                style: defaultStyle,
                name: 'vector'
            }),
            layers = getLayers();

        // Make sure to always set a unique ID to new features.
        vectorSource.on('change', function(e) {
            e.target.forEachFeature(function(f) {
                if (!f.getId()) {
                    f.setId(Date.now())
                }
            });
        });

        // Map
        var map = new ol.Map({
            target: mapPanel[0],
            layers: layers,
            view: new ol.View({
                center: [0, 0],
                zoom: 2,
                minZoom: 2,
                maxZoom: 20
            })
        });

        // Layer slider
        qgContainer.find('.nstSlider').nstSlider({
            "left_grip_selector": ".leftGrip",
            "value_changed_callback": function(cause, leftValue, rightValue) {
                changeLayerOpacity(leftValue / 100);
            }
        });

        var olGM = new olgm.OLGoogleMaps({map: map}); // map is the ol.Map instance
        olGM.activate();

        // Initial layers
        toggleLayer(0, 'googlehybrid');
        toggleLayer(1, 'osm');

        // The hidden input field where the coordinates are stored.
        var coordinatesField = mapContainer.next('.single-item').find('input:hidden');

        // Map interaction variables.
        var interaction,
            deleteMode = false,
            highlighted = [];  // The currently highlighted features.

        // Add an interaction for manually highlighting geometries.
        var highlightInteraction = getHighlightInteraction();
        map.addInteraction(highlightInteraction);

        // Action called when changing interaction mode.
        var interactionSwitch = qgContainer.find('[name="map-actions"]');
        interactionSwitch.on('change', handleMapInteractions);

        // Show the initial geometries on the map.
        showInitialGeometries();

        // Listen to changes on the vector layer and trigger initial change
        vectorLayer.on('change', function() {
            saveFeatures();
        });
        vectorLayer.changed();

        // Listen to all kinds of map actions.
        qgContainer.find('.js-btn-feature-count').click(function() { toggleMapOverlay('js-map-points') });
        qgContainer.find('.js-btn-delete-features').click(function() { toggleMapOverlay('js-map-delete-features') });
        qgContainer.find('.js-btn-coordinates-show').click(function() { toggleMapOverlay('js-map-coordinates') });
        qgContainer.find('.js-btn-search-show').click(function() { toggleMapOverlay('js-map-search') });
        qgContainer.find('.js-btn-overlay-close').click(hideMapOverlays);
        qgContainer.find('.js-btn-show-features').click(zoomToFeatures);
        qgContainer.find('.js-btn-confirm-delete-features').click(deleteAllFeatures);
        qgContainer.find('[name="map-layers-0"]').on('change', function() { toggleLayer(0, this.value) });
        qgContainer.find('[name="map-layers-1"]').on('change', function() { toggleLayer(1, this.value) });
        qgContainer.find('.js-btn-parse-coordinates').click(parseCoordinates);

        // Map search with Google
        var mapSearchInput = qgContainer.find('.js-map-search-field');
        if (mapSearchInput.length) {
            var mapSearch = new google.maps.places.SearchBox(mapSearchInput[0]);
            mapSearch.addListener('places_changed', function() {
                var places = this.getPlaces();
                if (places.length != 1) {
                  return;
                }
                var loc = places[0].geometry.location.toJSON();
                map.getView().setCenter(ol.proj.transform([loc.lng, loc.lat], 'EPSG:4326', 'EPSG:900913'));
                map.getView().setZoom(15);
            });
        }

        /**
         * A Select interaction used to manually highlight geometries.
         *
         * @returns {ol.interaction.Select}
         */
        function getHighlightInteraction() {
            return new ol.interaction.Select({
                style: selectStyle,
                // Features should not be selectable on the map by default.
                filter: function() { return false; }
            });
        }

        /**
         * (Re-)Attach actions for points on the map which are listed in the map
         * overlay.
         */
        function attachMapPointActions() {
            qgContainer.on('click', '.js-map-point-zoom', function() {
                var featureId = $(this).parent('li').data('feature-identifier');
                var feature = vectorSource.getFeatureById(featureId);
                zoomToFeature(feature);
            });
            qgContainer.on('click', '.js-map-point-remove', function() {
                // Remove a feature from the map.
                var featureId = $(this).parent('li').data('feature-identifier');
                deleteFeature(featureId);
            });
            qgContainer.find('.js-map-point-entry').bind({
                mouseenter: function() {
                    // Highlight feature on the map.
                    var featureId = $(this).data('feature-identifier');
                    var feature = vectorSource.getFeatureById(featureId);
                    highlightInteraction.getFeatures().push(feature);
                },
                mouseleave: function() {
                    // Unhighlight feature.
                    highlightInteraction.getFeatures().clear();
                }
            });
        }

        /**
         * Delete all features and activate the "draw" interaction.
         */
        function deleteAllFeatures() {
            vectorSource.clear();
            // Activate the draw interaction.
            interactionSwitch.filter(
                '[value="draw"]').attr('checked', true).trigger('change');
        }

        /**
         * Delete a certain feature from the map.
         *
         * @param featureId
         */
        function deleteFeature(featureId) {
            var feature = vectorSource.getFeatureById(featureId);
            if (feature) {
                vectorSource.removeFeature(feature);
            }
            highlightInteraction.getFeatures().clear();
        }

        /**
         * Zoom to a given feature on the map.
         *
         * @param feature
         */
        function zoomToFeature(feature) {
            map.getView().fit(feature.getGeometry(), map.getSize());
            map.getView().setZoom(15);
        }

        /**
         * Zoom to all features on the map.
         */
        function zoomToFeatures() {
            if (vectorSource.getFeatures().length) {
                map.getView().fit(vectorSource.getExtent(), map.getSize());
                map.getView().setZoom(Math.min(map.getView().getZoom(), 15));
            }
        }

        /**
         * Hide all map overlays.
         */
        function hideMapOverlays() {
            mapContainer.find('.map-overlay').hide();
        }

        /**
         * Toggle a map overlay by its class name.
         *
         * @param overlayClass
         */
        function toggleMapOverlay(overlayClass) {
            var overlaySelector = '.' + overlayClass;
            mapContainer.find('.map-overlay').not(overlaySelector).hide();
            mapContainer.find(overlaySelector).toggle();
        }

        /**
         * Show the initial geometries by parsing the the content of the
         * coordinates field and adding it to the map. If there are features,
         * the "edit" interaction is activated. If there are now features, the
         * "draw" mode is activated.
         */
        function showInitialGeometries() {
            if (coordinatesField.val()) {
                
                // Put initial features on map and set interaction type: Modify.
                // Zoom to features.
                var features = geomFormat.readFeatures(coordinatesField.val(), {
                    featureProjection: featureProjection
                });

                vectorSource.addFeatures(features);
                interactionSwitch.filter(
                    '[value="modify"]').attr('checked', true).trigger('change');
                zoomToFeatures();
                toggleDeleteMode(true);
            } else {
                // Set initial interaction type: Draw.
                interactionSwitch.filter(
                    '[value="draw"]').attr('checked', true).trigger('change');
                toggleDeleteMode(false);
            }
        }

        /**
         * Handle the map interactions (draw, modify, delete).
         */
        function handleMapInteractions() {
            // Remove the previous interaction mode.
            map.removeInteraction(interaction);

            // Unbind mouseover function used to delete features.
            $(map.getViewport()).unbind('mousemove');

            // No interaction selected (or interaction deselected)
            if (!$(this).is(':checked')) return;

            switch(this.value) {
                case 'draw':
                    // Draw (add) new features on the map.
                    interaction = new ol.interaction.Draw({
                        source: vectorSource,
                        type: 'Point',
                        maxPoints: 10,
                        style: defaultStyle
                      });
                    break;

                case 'modify':
                    // Modify (move) features on the map.
                    interaction = new ol.interaction.Modify({
                        features: new ol.Collection(
                            vectorSource.getFeatures()),
                        style: selectStyle
                    });
                    break;

                case 'delete':
                    // Delete (remove) features from the map.
                    interaction = new ol.interaction.Select({
                        layers: [vectorLayer]
                    });
                    interaction.on('select', function(event) {
                        if (event.selected.length) {
                            var feature = event.selected[0];
                            vectorSource.removeFeature(feature);
                            interaction.getFeatures().clear();
                        }
                    });

                    // This seems to be necessary just to get a little mouseover
                    // effect.
                    $(map.getViewport()).on('mousemove', function(e) {
                        unselectPreviousFeatures();
                        map.forEachFeatureAtPixel(
                            map.getEventPixel(e.originalEvent),
                            function(feature) {
                                feature.setStyle(deleteStyle);
                                highlighted.push(feature);
                        });
                    });
                    break;

                default:
                    break;
            }
            map.addInteraction(interaction);
        }

        /**
         * Return a list of all available layers, including the vector layer.
         *
         * @returns {*[]}
         */
        function getLayers() {
            function _getLayers(suffix) {
                return [
                    new olgm.layer.Google({
                        name: 'googlemaps' + suffix,
                        visible: false
                    }),
                    new olgm.layer.Google({
                        name: 'googlesatellite' + suffix,
                        mapTypeId: google.maps.MapTypeId.SATELLITE,
                        visible: false
                    }),
                    new olgm.layer.Google({
                        name: 'googlehybrid' + suffix,
                        mapTypeId: google.maps.MapTypeId.HYBRID,
                        visible: false
                    }),
                    new ol.layer.Tile({
                        name: 'osm' + suffix,
                        source: new ol.source.OSM(),
                        visible: false
                    }),
                    new ol.layer.Tile({
                        name: 'komoot' + suffix,
                        visible: false,
                        source: new ol.source.XYZ({
                            attributions: '&copy; <a href="http://www.komoot.de/">Komoot</a>, &copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
                            url: 'http://a.tile.komoot.de/komoot-2/{z}/{x}/{y}.png'
                        })
                    }),
                    new ol.layer.Tile({
                        name: 'aerial' + suffix,
                        visible: false,
                        source: new ol.source.XYZ({
                            attributions: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
                            url: 'http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
                        })
                    }),
                    new ol.layer.Tile({
                        name: 'opentopo' + suffix,
                        visible: false,
                        source: new ol.source.XYZ({
                            attributions: 'Map data: &copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
                            url: 'http://{a-c}.tile.opentopomap.org/{z}/{x}/{y}.png'
                        })
                    }),
                    new ol.layer.Tile({
                        name: 'landscape' + suffix,
                        visible: false,
                        source: new ol.source.XYZ({
                            attributions: '&copy; <a href="http://www.thunderforest.com/">Thunderforest</a>, &copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
                            url: 'http://{a-c}.tile.thunderforest.com/landscape/{z}/{x}/{y}.png'
                        })
                    }),
                    new ol.layer.Tile({
                        name: 'worldtopo' + suffix,
                        visible: false,
                        source: new ol.source.XYZ({
                            attributions: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ, TomTom, Intermap, iPC, USGS, FAO, NPS, NRCAN, GeoBase, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), and the GIS User Community',
                            url: 'http://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}'
                        })
                    })
                ];
            }
            return _getLayers('_0').concat(_getLayers('_1')).concat([vectorLayer]);
        }

        /**
         * Change the opacity of the layers. Differentiates between layers of
         * "group" 0 and 1.
         *
         * @param opacity: Between 0 and 1.
         */
        function changeLayerOpacity(opacity) {
            for (var i=0; i<layers.length; i++) {
                var layer = layers[i];
                // Never change opacity of the vector layer.
                if (layer.get('name') == 'vector') continue;
                if (layer.get('name').endsWith('_0')) {
                    layer.setOpacity(1 - opacity);
                } else {
                    layer.setOpacity(opacity);
                }
            }
        }

        /**
         * Toggle the visibility of a certain layer while hiding all the others.
         * Never hide the layer with name "vector" (the one used for the points)
         *
         * @param layerGroupIndex
         * @param layerName
         */
        function toggleLayer(layerGroupIndex, layerName) {
            var suffix = layerGroupIndex == 0 ? '_0' : '_1';
            for (var i=0; i<layers.length; i++) {
                var layer = layers[i];
                if (layer.get('name').endsWith(suffix)) {
                    layer.setVisible(layer.get('name') == layerName + suffix);
                }
            }
        }

        /**
         * Unselect previously selected features.
         */
        function unselectPreviousFeatures() {
            var i;
            for(i = 0; i < highlighted.length; i++) {
                highlighted[i].setStyle(null);
            }
            highlighted = [];
        }

        /**
         * Save features on the map: Store coordinates in the hidden field,
         * toggle available interaction modes and update list of points on the
         * map.
         */
        function saveFeatures() {
            var features = vectorSource.getFeatures();
            if (features.length) {
                coordinatesField.val(geomFormat.writeFeatures(features, {
                    featureProjection: featureProjection
                }));
                toggleDeleteMode(true);
            } else {
                coordinatesField.val('');
                toggleDeleteMode(false);
            }
            updatePointsList();
            attachMapPointActions();
        }

        /**
         * Update the list of points on the map. Also update the counter of
         * features on the map.
         */
        function updatePointsList() {
            var features = vectorSource.getFeatures();

            // Update feature count button
            var thisMapContainer = $(mapContainer).closest('.map-container');
            thisMapContainer.find('.js-btn-feature-count')
                .html(features.length);

            var pointsList = thisMapContainer.find('.map-points-list');
            var pointsHtml = '<p>' + pointsList.data('empty-text') + '</p>';

            if (features.length) {
                pointsHtml = $('<ul class="map-point-entries"></ul>');

                features.forEach(function(f) {
                    var coords = f.getGeometry().getCoordinates();
                    var coordsTransformed = ol.proj.transform(coords, featureProjection, dataProjection);

                    // Round the coordinates to 6 decimals.
                    var coordsLength = coordsTransformed.length;
                    while (coordsLength--) {
                        coordsTransformed[coordsLength] = coordsTransformed[coordsLength].toFixed(6);
                    }

                    // Prepare a list entry for each point.
                    var coordsEntry = $('<li class="js-map-point-entry" data-feature-identifier="' + f.getId() + '"></li>');
                    var zoomLink = $('<span class="map-point-entry-zoom js-map-point-zoom"><svg class="icon-lines is-inline"><use xlink:href="#icon-location2"></use></svg></span>');
                    var removeLink = '';
                    if (settings.editable) {
                        removeLink = $('<span class="map-point-entry-remove js-map-point-remove"><svg class="icon-lines is-inline"><use xlink:href="#icon-bin"></use></svg></span>');
                    }
                    var coordsText = $('<span class="js-map-point-zoom">' + coordsTransformed.join(', ') + '</span>');
                    coordsEntry.append(zoomLink, removeLink, coordsText);

                    pointsHtml.append(coordsEntry);
                });
            }
            pointsList.html(pointsHtml);
        }

        /**
         * Enable or disable the buttons to modify/edit existing points.
         *
         * @param enabled
         */
        function toggleDeleteMode(enabled) {
            if (enabled != deleteMode) {
                // Mode changed
                deleteMode = enabled;
                var btnToggle = $(mapPanel).closest('.map-container').find('.map-btn-toggle');
                btnToggle.each(function() {
                    $(this).toggleClass('map-btn-disabled', !deleteMode);
                    $('#' + $(this).attr('for')).prop('disabled', !deleteMode);
                });
                if (!deleteMode) {
                    // No points left, deactivate modify and delete mode if enabled.
                    interactionSwitch.filter(
                        '[value="delete"]').attr('checked', false).trigger('change');
                    interactionSwitch.filter(
                        '[value="modify"]').attr('checked', false).trigger('change');
                }
            }
        }

        /**
         * Parse the coordinates clicked in the corresponding field. If the
         * coordinates are valid, add the point on the map and zoom to it.
         */
        function parseCoordinates() {
            var logField = mapContainer.find('.map-coordinates-log');
            var coordsField = mapContainer.find('.map-coordinates-field');
            if (!coordsField.val()) return;

            var msg = document.createElement('p');
            var coords = getCoordinatesFromText(coordsField.val());
            if (!coords.valid) {
                $(msg).html(coords.msg).addClass('error');
            } else {
                var coordsTransformed = ol.proj.transform(coords.coords, dataProjection, featureProjection);
                var feature = new ol.Feature(new ol.geom.Point(coordsTransformed));
                vectorSource.addFeatures([feature]);
                zoomToFeature(feature);
                $(msg).html('The point was successfully added.').addClass('success');
                coordsField.val('');
            }
            logField.html(msg);
        }

        /**
         * Parse a string of coordinates. Returns an object with the coordinates or
         * error message.
         *
         * Caution: The coordinates are reversed to be used by OpenLayers,
         * input: "Latitude, Longitude"
         * output: [lon, lat]
         *
         * @param coords_text. Coordinates as string. Must be of format "Latitude,
         * Longitude", eg. "46.9526, 7.4352".
         * @returns {{valid: boolean, coords: Array, msg: string}}
         */
        function getCoordinatesFromText(coords_text) {
            var coordinates = {
                valid: false,
                coords: [],
                msg: ''
            };

            var coords_list = coords_text.split(',');
            if (coords_list.length != 2) {
                coordinates.msg = 'Must be of format "Latitude, Longitude", eg. ' +
                    '46.9526, 7.4352';
                return coordinates;
            }

            coordinates.coords = coords_list.map(function(c) {
                var asFloat = parseFloat(c);
                if (isNaN(asFloat)) {
                    coordinates.msg = 'Coordinates do not contain valid number ' +
                        'values.'
                }
                return asFloat;
            }).reverse();
            coordinates.valid = coordinates.msg == '';

            return coordinates;
        }

        /**
         * The default style for features on the map.
         *
         * @returns {ol.style.Style}
         */
        function getDefaultVectorStyle() {
            return new ol.style.Style({
                image: new ol.style.Circle({
                    radius: 6,
                    fill: new ol.style.Fill({
                        color: '#f5f900'
                    }),
                    stroke: new ol.style.Stroke({
                        color: 'black',
                        width: 2.25
                    })
                })
            });
        }

        /**
         * The style when a feature is selected.
         *
         * @returns {ol.style.Style}
         */
        function getSelectVectorStyle() {
            return new ol.style.Style({
                image: new ol.style.Circle({
                    radius: 7,
                    fill: new ol.style.Fill({
                        color: 'rgba(255, 255, 255, 1)'
                    }),
                    stroke: new ol.style.Stroke({
                        color: '#dc7d35',
                        width: 1.25
                    })
                })
            });
        }

        /**
         * The style for mouseover on features to be deleted.
         *
         * @returns {ol.style.Style}
         */
        function getDeleteVectorStyle() {
            return new ol.style.Style({
                image: new ol.style.Circle({
                    radius: 7,
                    fill: new ol.style.Fill({
                        color: 'rgba(255, 0, 0, 0.2)'
                    }),
                    stroke: new ol.style.Stroke({
                        color: 'rgba(255, 0, 0, 0.6)',
                        width: 1.25
                    })
                })
            });
        }
    };
}(jQuery));
