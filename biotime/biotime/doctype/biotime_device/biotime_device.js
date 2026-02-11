frappe.ui.form.on("BioTime Device", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.biotime_device_id) {
			frm.add_custom_button(__("Ping Device"), function () {
				frm.call("ping_device").then((r) => {
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: __("Device is {0}", [r.message.status]),
							indicator: r.message.status === "Online" ? "green" : "red",
						});
						frm.reload_doc();
					} else {
						frappe.msgprint(r.message ? r.message.message : "Failed");
					}
				});
			});

			frm.add_custom_button(__("Sync from BioTime"), function () {
				frm.call("sync_from_biotime").then((r) => {
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: __("Device synced"),
							indicator: "green",
						});
						frm.reload_doc();
					}
				});
			});
		}
	},
});
