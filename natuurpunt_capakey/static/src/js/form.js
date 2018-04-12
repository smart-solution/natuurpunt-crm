openerp.natuurpunt_capakey = function (instance) {
    instance.web.ActionManager = instance.web.ActionManager.extend({

        ir_actions_act_close_wizard_and_reload_capakey: function (action, options) {
            if (!this.dialog) {
                options.on_close();
            }
            this.dialog_stop();
			var key = "building_capakey"
		    var value = action.context.capakey
            this.inner_widget.views[this.inner_widget.active_view].controller.reload_replace(key,value);
            return $.when();
        },
    });

	instance.web.FormView = instance.web.FormView.extend({
		reload_replace: function (key,value) {
            var self = this;
            return this.reload_mutex.exec(function() {
                if (self.dataset.index == null) {
                    self.trigger("previous_view");
                    return $.Deferred().reject().promise();
                }
                if (self.dataset.index == null || self.dataset.index < 0) {
                    return $.when(self.on_button_new());
                } else {
                    var fields = _.keys(self.fields_view.fields);
                    fields.push('display_name');
                    return self.dataset.read_index(fields,
                        {
                            context: {
                                'bin_size': true,
                                'future_display_name': true
                            },
                            check_access_rule: true
                        }).then(function(r) {
                            r[key] = value
                            self.trigger('load_record', r);
                        }).fail(function (){
                            self.do_action('history_back');
                        });
                }
            });
        },
	});

}
