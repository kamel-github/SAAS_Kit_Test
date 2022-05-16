odoo.define('openerp_saas_tenant.ListRenderer', function (require) {
"use strict";
    var list_renderer = require('web.ListRenderer');
    const framework = require('web.framework');
    var Dialog = require('web.Dialog');
    var session = require('web.session');

    var user = session.uid
    list_renderer.include({
        start : function(){
//            var self = this;
            this._super();
//            this.chartContainer();
            if (this.state.model == 'saas.service'){
                this.googlePieChart1();
//                framework.blockUI();
            }
        },

        async _renderView() {
            const oldPagers = this.pagers;
            let prom;
            let tableWrapper;
            if (this.state.count > 0 || !this.noContentHelp) {
                // render a table if there are records, or if there is no no content
                // helper (empty table in this case)
                this.pagers = [];

                const orderedBy = this.state.orderedBy;
                this.hasHandle = orderedBy.length === 0 || orderedBy[0].name === this.handleField;
                this._computeAggregates();

                const $table = $(
                    '<table class="o_list_table table table-sm table-hover table-striped"/>'
                );
                $table.toggleClass('o_list_table_grouped', this.isGrouped);
                $table.toggleClass('o_list_table_ungrouped', !this.isGrouped);
                const defs = [];
                this.defs = defs;
                if (this.isGrouped) {
                    $table.append(this._renderHeader());
                    $table.append(this._renderGroups(this.state.data));
                    $table.append(this._renderFooter());

                } else {
                    $table.append(this._renderHeader());
                    $table.append(this._renderBody());
                    $table.append(this._renderFooter());
                }
    //            console.log($table);

                tableWrapper = Object.assign(document.createElement('div'), {
                    className: 'table-responsive',
                });
                tableWrapper.appendChild($table[0]);
                /////////////////////////////////////////////////////////////////////////////////
                if (this.state.model == 'saas.service'){
                console.log(this.state.model);
                    const $table2 = $('<table class="o_list_table table table-sm table-hover"/>');
                    $table2.append('<tbody><tr><td style="text-align: center; vertical-align: middle;font-size:18px;"><div id="db_size"><b>Database Analytics</b></div></td><td style="text-align: center; vertical-align: middle;font-size:18px;"><div id="fielstore_size"><b>Filestore Analytics</b></div></td></tr><tr><td><div id="piechart1"  ></div></td><td><div id="piechart2"></div></td></tr></tbody>');
                    tableWrapper.appendChild($table2[0]);
                }
                /////////////////////////////////////////////////////////////////////////////////
                delete this.defs;
                prom = Promise.all(defs);
            }

            await Promise.all([this._super.apply(this, arguments), prom]);

            this.el.innerHTML = "";
            this.el.classList.remove('o_list_optional_columns');

            // destroy the previously instantiated pagers, if any
            oldPagers.forEach(pager => pager.destroy());

            // append the table (if any) to the main element
            if (tableWrapper) {
                this.el.appendChild(tableWrapper);
                if (document.body.contains(this.el)) {
                    this.pagers.forEach(pager => pager.on_attach_callback());
                }
                if (this.optionalColumns.length) {
                    this.el.classList.add('o_list_optional_columns');
                    this.$('table').append(
                        $('<i class="o_optional_columns_dropdown_toggle fa fa-ellipsis-v"/>')
                    );
                    this.$el.append(this._renderOptionalColumnsDropdown());
                }
                if (this.selection.length) {
                    const $checked_rows = this.$('tr').filter(
                        (i, el) => this.selection.includes(el.dataset.id)
                    );
                    $checked_rows.find('.o_list_record_selector input').prop('checked', true);
                    if ($checked_rows.length === this.$('.o_data_row').length) { // all rows are checked
                        this.$('thead .o_list_record_selector input').prop('checked', true);
                    }
                }
            }

            // display the no content helper if necessary
            if (!this._hasContent() && !!this.noContentHelp) {
                this._renderNoContentHelper();
            }
        },

        googlePieChart1 : function(){
            let db_info,total_db_size;
            let filestore_info,total_filestore_size;
            db_info = this.getDbInfo('database');
            filestore_info = this.getDbInfo('filestore');

//            console.log(db_info);
//            console.log(filestore_info);
            total_db_size = parseFloat(db_info[1][1])+parseFloat(db_info[2][1]);
            total_filestore_size = parseFloat(filestore_info[1][1])+parseFloat(filestore_info[2][1]);


            setTimeout(function(){
                    google.charts.load("visualization", "1", {'packages':['corechart']});
                    google.charts.setOnLoadCallback(drawChart1);
                    google.charts.setOnLoadCallback(drawChart2);

                    function drawChart1() {
                        console.log(db_info);
                        var data = google.visualization.arrayToDataTable(db_info);
                        let i = 90;
                        var options = {
                            title: 'Database Total Size '+total_db_size.toFixed(2)+" GB",
                            titleTextStyle: {
                                                fontSize: 15, // 12, 18 whatever you want (don't specify px)
                                                bold: true,    // true or false
                                            },
                            width: 640,
                            height: 350,
                            pieSliceText: 'none',
                            legend: { position: 'labeled',
                                      labeledValueText: 'both',
                                      alignment:'center',
                                      textStyle: {
                                          color: 'black',
                                          fontSize: 12 }, strokeColor: {color: 'black'},
                             },
                            tooltip: { trigger: 'none' },
    //                        is3D: true,
                        };
                        var chart = new google.visualization.PieChart(document.getElementById('piechart1'));
                        chart.draw(data, options);

                    };
                    function drawChart2() {
                        console.log(filestore_info);
                        var data = google.visualization.arrayToDataTable(filestore_info);
                        var options = {
                            title: 'Filestore Total Size '+total_filestore_size.toFixed(2)+" GB",
                            titleTextStyle: {
                                                fontSize: 15, // 12, 18 whatever you want (don't specify px)
                                                bold: true,    // true or false
                                            },
                            width: 640,
                            height: 350,
                            pieSliceText: 'none',
                            legend: { position: 'labeled',
                                      labeledValueText: 'both',
                                      alignment:'center',
                                      textStyle: {
                                          color: 'black',
                                          fontSize: 12 }, strokeColor: {color: 'black'},
                            },
                            tooltip: { trigger: 'none' },
    //                         is3D: true,
                        };
                        var chart = new google.visualization.PieChart(document.getElementById('piechart2'));
                        chart.draw(data, options);

                    };
                    }, 1000);

        },

        getDbInfo : function(type){
            var model = this.state.model;
            var dict = {};
            var ret = [];
            $.ajax({
                url : '/db/space_info/',
                async : false,
                data : {    model: model, type:type },
                success : function(data) {
                    var data1 = JSON.parse(data);

//                    if( parseFloat(data1.dbInfo.default_db_size) < parseFloat(data1.dbInfo.used_db_size)){
//                         framework.blockUI();
//                    }
//                    if( parseFloat(data1.dbInfo.default_filestore_size) < parseFloat(data1.dbInfo.used_filestore_size)){
//                         framework.blockUI();
//                    }
                    let db_consumed_size = 0;
                    let filestore_consumed = 0;

                    if(data1.dbInfo.default_db_size){
                        db_consumed_size = parseFloat(data1.dbInfo.default_db_size) - parseFloat(data1.dbInfo.used_db_size);
                    }

                    if(data1.dbInfo.default_filestore_size){
                        filestore_consumed = parseFloat(data1.dbInfo.default_filestore_size)-parseFloat(data1.dbInfo.used_filestore_size);
                    }
                    console.log(db_consumed_size+"---"+filestore_consumed);
                    ret.push(['Type', 'volume']);
                    if(db_consumed_size <= 0 || filestore_consumed <= 0){
                            var div = document.createElement("div");
                            div.classList.add('popup_div');
                            var newContent = document.createElement("div");
                            newContent.style.marginTop= 250+"px";
                            newContent.style.padding = 35+"px";
                            newContent.style.background = "none no-repeat scroll 0 0 #fff";
                            newContent.classList.add('container');
                            newContent.style.height =150+"px";
                            newContent.style.width =500+"px";
                            newContent.style.borderColor= "red green blue pink";
                            var text1 = document.createElement("h5");

                            if ((type=='database')&&(db_consumed_size <= 0)){

                                var text_content1 = document.createTextNode("Your database size limit is exceeded from allocated size ...!");
                                db_consumed_size = 0;

                            }else if((type=='filestore')&&(filestore_consumed <= 0)){

                                var text_content1 = document.createTextNode('Your filestore size limit is exceeded from allocated size ...!');
                                filestore_consumed=0;

                            }

                            if(text_content1){
                                text1.appendChild(text_content1);
                                newContent.appendChild(text1);
                                var text2 = document.createElement("h6");
                                var text_content2 = document.createTextNode("Please purchase more space");
                                text2.appendChild(text_content2);
                                newContent.appendChild(text2);
                                var space = document.createElement("br");
                                newContent.appendChild(space);
                                div.appendChild(newContent);

                                var sub_button = document.createElement("button");
                                sub_button.classList.add('submit_button');
                                var sub_button_text = document.createTextNode("OK");
                                sub_button.appendChild(sub_button_text);
                                sub_button.style.width =76+"px";
                                sub_button.style.float ="right";
                                sub_button.style.backgroundColor ="#4CAF50";
                                sub_button.style.borderRadius= 2+"px";
                                sub_button.style.marginRight= 10+"px";
                                sub_button.style.height =31+"px";
                                newContent.appendChild(sub_button);
                                div.style.width =100+"%";
                                div.style.backgroundColor = "rgb(0,0,0,0.4)";
                                div.style.height =100+"%";
                                div.style.position ="absolute";
                                div.style.display ="block";
                            }
                             if((data1.dbInfo.default_db_size)||(data1.dbInfo.default_filestore_size)){
                                document.body.appendChild(div);
                             }
                    }


                        if (type == 'filestore'){
                            ret.push(['Unused Filestore Size '+filestore_consumed.toFixed(2)+" GB", filestore_consumed]);
                            ret.push(["Used Filestore Size "+data1.dbInfo.used_filestore_size.toFixed(2)+" GB", data1.dbInfo.used_filestore_size]);
                        }else{
                            ret.push(["Unused Database Size "+db_consumed_size.toFixed(2)+" GB", db_consumed_size]);
                            ret.push(["Used Database Size "+data1.dbInfo.used_db_size.toFixed(2)+" GB", data1.dbInfo.used_db_size ]);
                        }
                        if (data1.exist == true){
                            alert("Instance name is not available")
                            ret = false
                        }

                }
            });
            $('.submit_button').on('click',function(){
                if (user > 5){
                    framework.blockUI();
                }
                else{
                    $(".popup_div").hide()
                }
            })

            return ret;
        },
    });

})
//
//
//odoo.define('openerp_saas_tenant.settings', function (require) {
//    "use strict";
//    const BaseSetting = require('base.settings');
//    var FormRenderer = require('web.FormRenderer');
//
//
//    var BaseSettingRenderer = FormRenderer.extend(BaseSetting, {
//        init: function () {
//            this._super.apply(this, arguments);
//              console.log('our code');
//        },
//
//        _onSettingTabClick: function (event) {
//            console.log('our code');
//            this._super();
//        },
//
//    });
//
//    setTimeout(function(){  $('div#website_action_setting > button:eq(2)').css('display', 'none');
//                            console.log('done');
//                          }, 3500);
//
//    return BaseSettingRenderer;
//})

odoo.define('base.settings', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var core = require('web.core');
var FormView = require('web.FormView');
var FormController = require('web.FormController');
var FormRenderer = require('web.FormRenderer');
var view_registry = require('web.view_registry');


var QWeb = core.qweb;
var _t = core._t;

var BaseSettingRenderer = FormRenderer.extend({
    events: _.extend({}, FormRenderer.prototype.events, {
        'click .tab': '_onSettingTabClick',
        'keyup .searchInput': '_onKeyUpSearch',
    }),

    init: function () {
        this._super.apply(this, arguments);
        this.activeView = false;
        this.activeTab = false;
    },

    /**
     * @override
     * overridden to show a message, informing user that there are changes
     */
    confirmChange: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {

            if (!self.$(".o_dirty_warning").length) {
                self.$('.o_statusbar_buttons')
                    .append($('<span/>', {text: _t("Unsaved changes"), class: 'text-muted ml-2 o_dirty_warning'}))
            }
        });
    },
    /**
     * @override
     */
    on_attach_callback: function () {
        this._super.apply(this, arguments);
        // set default focus on searchInput
        this.searchInput.focus();
    },

    /**
     * @override
     */
    displayTranslationAlert: function () {
        // Translation alerts are disabled for res.config.settings:
        // those are designed to warn user to translate field he just changed, but
        // * in res.config.settings almost all fields marked as changed (because
        //   it's not a usual record and all values are set via default_get)
        // * page is reloaded after saving, so those alerts would be visible
        //   only for short time after clicking Save
    },
    /**
     * initialize modules list.
     * remove module that restricted in groups
     * data contains
     *  {
     *     key: moduel key
     *     string: moduel string
     *     imgurl: icon url
     *  }
     *
     * @private
     */
    _initModules: function () {
        var self = this;
        this.modules = [];
        _.each(this.$('.app_settings_block'), function (settingView, index) {
            var group = !$(settingView).hasClass('o_invisible_modifier');
            var isNotApp = $(settingView).hasClass('o_not_app');
            if(group && !isNotApp) {
                var data = $(settingView).data();
                data.string = $(settingView).attr('string') || data.string;
                self.modules.push({
                    key: data.key,
                    string: data.string,
                    imgurl: self._getAppIconUrl(data.key),
                });
            } else {
                $(settingView).remove();
            }
        });
    },
    /**
     * initialize searchtext variable
     * initialize jQuery search input element
     *
     * @private
     */
    _initSearch: function () {
        this.searchInput = this.$('.searchInput');
        if (this.searchText) {
            this.searchInput.val(this.searchText);
            this._onKeyUpSearch();
        } else {
            this.searchText = "";
        }
    },
    /**
     * find current app index in modules
     *
     */
    _currentAppIndex: function () {
        var self = this;
        var index = _.findIndex(this.modules, function (module) {
            return module.key === self.activeSettingTab;
        });
        return index;
    },
    /**
     *
     * @private
     * @param {string} module
     * @returns {string} icon url
     */
    _getAppIconUrl: function (module) {
        return module === "general_settings" ? "/base/static/description/settings.png" : "/"+module+"/static/description/icon.png";
    },
    /**
     *
     * @private
     * @param {string} imgurl
     * @param {string} string(moduel name)
     * @returns {object}
     */
    _getSearchHeader: function (imgurl, string) {
        return $(QWeb.render('BaseSetting.SearchHeader', {
            imgurl: imgurl,
            string: string
        }));
    },
    /**
     * move to selected setting
     *
     * @private
     * @param {int} index
     */
    _moveToTab: function (index) {
        this.currentIndex = !index || index === -1 ? 0 : (index === this.modules.length ? index - 1 : index);
        if (this.currentIndex !== -1) {
            if (this.activeView) {
                this.activeView.addClass("o_hidden");
            }
            if (this.activeTab) {
                this.activeTab.removeClass("selected");
            }
            var view = this.modules[this.currentIndex].settingView;
            var tab = this.$(".tab[data-key='" + this.modules[this.currentIndex].key + "']");
            view.removeClass("o_hidden");
            this.activeView = view;
            this.activeTab = tab;
            tab.addClass("selected");
        }
    },

    _onSettingTabClick: function (event) {
        this.searchInput.focus();
        if (this.searchText.length > 0) {
            this.searchInput.val('');
            this.searchText = "";
            this._searchSetting();
        }
        $('div#website_action_setting > button:eq(2)').css('display', 'none');
         setTimeout(function(){  $('div#website_action_setting > button:eq(2)').css('display', 'none');
                            console.log('done');
                          }, 250);

        var settingKey = this.$(event.currentTarget).data('key');
        this._moveToTab(_.findIndex(this.modules, function (m) {
            return m.key === settingKey;
        }));


    },

    _onKeyUpSearch: function (event) {
        this.searchText = this.searchInput.val();
        this.activeTab.removeClass('selected');
        this._searchSetting();
    },
    /**
     * reset setting view
     *
     * @private
     */
    _resetSearch: function () {
        this.searchInput.val("");
        _.each(this.modules, function (module) {
            module.settingView.addClass('o_hidden');
            module.settingView.find('.o_setting_box').removeClass('o_hidden');
            module.settingView.find('h2').removeClass('o_hidden');
            module.settingView.find('.settingSearchHeader').addClass('o_hidden');
            module.settingView.find('.o_settings_container').addClass('mt16');
        });
        this.activeTab.removeClass('o_hidden').addClass('selected');
        this.activeView.removeClass('o_hidden');
    },

    _render: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function() {
            self._initModules();
            self._renderLeftPanel();
            self._initSearch();
        });
    },

    _renderLeftPanel: function () {
        var self = this;
        _.each(this.modules, function (module) {
            module.settingView = self.$('.app_settings_block[data-key="' + module.key + '"]');
            module.settingView.addClass("o_hidden");
            module.settingView.prepend(self._getSearchHeader(module.imgurl, module.string));
        });

        this._renderTabs();
        this._moveToTab(this.currentIndex || this._currentAppIndex());

    },

    _renderTabs: function () {
        var tabs = $(QWeb.render('BaseSetting.Tabs', {tabItems : this.modules}));
        tabs.appendTo(this.$(".settings_tab"));
    },
    /**
     * search setting in DOM
     *
     * @private
     */
    _searchSetting: function () {
        var self = this;
        this.count = 0;
        _.each(this.modules, function (module) {
            self.inVisibleCount = 0;
            module.settingView.find('.o_setting_box').addClass('o_hidden');
            module.settingView.find('h2').addClass('o_hidden');
            module.settingView.find('.settingSearchHeader').addClass('o_hidden');
            module.settingView.find('.o_settings_container').removeClass('mt16');
            var resultSetting = module.settingView.find(".o_form_label:containsTextLike('" + self.searchText + "')");
            if (resultSetting.length > 0) {
                resultSetting.each(function () {
                    var settingBox = $(this).closest('.o_setting_box');
                    if (!settingBox.hasClass('o_invisible_modifier')) {
                        settingBox.removeClass('o_hidden');
                        $(this).html(self._wordHighlighter($(this).html(), self.searchText));
                    } else {
                        self.inVisibleCount++;
                    }
                });
                if (self.inVisibleCount !== resultSetting.length) {
                    module.settingView.find('.settingSearchHeader').removeClass('o_hidden');
                    module.settingView.removeClass('o_hidden');
                }
            } else {
                ++self.count;
            }
        });

        this.count === _.size(this.modules) ? this.$('.notFound').removeClass('o_hidden') : this.$('.notFound').addClass('o_hidden');
        if (this.searchText.length === 0) {
            this._resetSearch();
        }
    },
    /**
     * highlight search word
     *
     * @private
     * @param {string} text
     * @param {string} word
     */
    _wordHighlighter: function (text, word) {
        if (text.indexOf('highlighter') !== -1) {
            text = text.replace('<span class="highlighter">', "");
            text = text.replace("</span>", "");
        }
        var match = text.search(new RegExp(word, "i"));
        word = text.substring(match, match + word.length);
        var highlightedWord = "<span class='highlighter'>" + word + '</span>';
        return text.replace(word, highlightedWord);
    },
});

var BaseSettingController = FormController.extend({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        button_clicked: '_onButtonClicked',
    }),
    init: function () {
        this._super.apply(this, arguments);
        this.disableAutofocus = true;
        this.renderer.activeSettingTab = this.initialState.context.module;
    },
    /**
     * Settings view should always be in edit mode, so we have to override
     * default behaviour
     *
     * @override
     */
    willRestore: function () {
        this.mode = 'edit';
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onButtonClicked: function (ev) {

        var self = this;

        if (ev.data.attrs.name !== 'execute' && ev.data.attrs.name !== 'cancel') {
            var recordID = ev.data.recordID;
            var _super = this._super;
            var args = arguments;
            this._discardChanges(recordID, { noAbandon: true }).then(function () {
                _super.apply(self, args);
            });
        } else {
            this._super.apply(this, arguments);
        }
    },

});

var BaseSettingsModel = BasicModel.extend({
    /**
     * @override
     */
    save: function (recordID) {
        var self = this;
        return this._super.apply(this, arguments).then(function (result) {

            // we remove here the res_id, because the record should still be
            // considered new.  We want the web client to always perform a
            // default_get to fetch the settings anew.
            delete self.localData[recordID].res_id;
            return result;
        });
    },
});

var BaseSettingView = FormView.extend({
    jsLibs: [],
    config: _.extend({}, FormView.prototype.config, {
        Model: BaseSettingsModel,
        Renderer: BaseSettingRenderer,
        Controller: BaseSettingController,
    }),
});

view_registry.add('base_settings', BaseSettingView);

return {
    Model: BaseSettingsModel,
    Renderer: BaseSettingRenderer,
    Controller: BaseSettingController,
};
});
