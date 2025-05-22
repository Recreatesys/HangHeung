import {patch} from "@web/core/utils/patch";
import {PosStore} from "@point_of_sale/app/store/pos_store";
const {DateTime} = luxon;

patch(PosStore.prototype, {
    async processServerData() {
        await super.processServerData();
        for (const program of this.models["loyalty.program"].getAll()) {
            // console.log(program, 1111111)
            if (program.date_to) {
                const parts = program.date_to.invalid.explanation.split('"');
                const extractedDate = parts.length >= 2 ? parts[1] : null;
                program.date_to = DateTime.fromFormat(extractedDate, "yyyy-MM-dd HH:mm:ss", {zone: "utc"});
                program.date_to = DateTime.fromISO(program.date_to);
            }
            if (program.date_from) {
                const parts1 = program.date_from.invalid.explanation.split('"');
                const extractedDate1 = parts1.length >= 2 ? parts1[1] : null;
                program.date_from = DateTime.fromFormat(extractedDate1, "yyyy-MM-dd HH:mm:ss", {zone: "utc"});
                program.date_from = DateTime.fromISO(program.date_from);
            }
        }
    },
});