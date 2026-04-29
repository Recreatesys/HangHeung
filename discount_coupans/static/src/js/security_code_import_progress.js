/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

class SecurityCodeImportProgress extends Component {
    static template = "discount_coupans.SecurityCodeImportProgress";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            running: false,
            done: false,
            currentBatch: 0,
            totalBatches: 0,
            totalRows: 0,
            updated: 0,
            noChange: 0,
            skipped: 0,
            message: "",
            errorMessage: "",
        });
    }

    get percent() {
        if (!this.state.totalBatches) return 0;
        return Math.round((this.state.currentBatch / this.state.totalBatches) * 100);
    }

    async startImport() {
        const record = this.props.record;
        if (!record || !record.data || !record.data.file_data) {
            this.notification.add(_t("Please upload an Excel file first."), { type: "warning" });
            return;
        }

        this.state.running = true;
        this.state.done = false;
        this.state.errorMessage = "";
        this.state.currentBatch = 0;
        this.state.totalBatches = 0;
        this.state.totalRows = 0;
        this.state.updated = 0;
        this.state.noChange = 0;
        this.state.skipped = 0;
        this.state.message = _t("Saving file...");

        try {
            // Persist the uploaded file so the server can read it.
            await record.save({ reload: false });
            const wizardId = record.resId;
            if (!wizardId) {
                throw new Error(_t("Could not save the wizard record."));
            }

            this.state.message = _t("Parsing Excel...");
            const parseResult = await this.orm.call(
                "loyalty.security.code.import.wizard",
                "action_parse_file",
                [[wizardId]],
            );
            this.state.totalRows = parseResult.total_rows || 0;
            this.state.totalBatches = parseResult.total_batches || 0;

            if (this.state.totalRows === 0) {
                this.state.message = _t("No rows found in file.");
                this.state.running = false;
                return;
            }

            this.state.message = _t("Found %s rows. Importing in %s batch(es) of 2000...",
                this.state.totalRows, this.state.totalBatches);

            for (let i = 0; i < this.state.totalBatches; i++) {
                const batchResult = await this.orm.call(
                    "loyalty.security.code.import.wizard",
                    "action_process_batch",
                    [[wizardId], i],
                );
                this.state.currentBatch = i + 1;
                this.state.updated = batchResult.updated || 0;
                this.state.noChange = batchResult.no_change || 0;
                this.state.skipped = batchResult.skipped || 0;
                this.state.message = _t("Batch %s / %s done", this.state.currentBatch, this.state.totalBatches);
            }

            this.state.message = _t("Finalizing...");
            await this.orm.call(
                "loyalty.security.code.import.wizard",
                "action_finalize",
                [[wizardId]],
            );

            this.state.message = _t("Import complete.");
            this.state.done = true;

            // Reload form to show result_summary populated by finalize.
            await record.load();
        } catch (err) {
            this.state.errorMessage = (err && err.message) ? err.message : String(err);
            this.notification.add(this.state.errorMessage, { type: "danger" });
        } finally {
            this.state.running = false;
        }
    }
}

export const securityCodeImportProgress = {
    component: SecurityCodeImportProgress,
};

registry.category("view_widgets").add("security_code_import_progress", securityCodeImportProgress);
