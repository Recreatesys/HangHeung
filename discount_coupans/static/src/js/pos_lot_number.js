/* global waitForWebfonts */

import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { EditListPopup } from "@point_of_sale/app/store/select_lot_popup/select_lot_popup";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { makeAwaitable, ask } from "@point_of_sale/app/store/make_awaitable_dialog";

patch(PosStore.prototype, {
    async editLots(product, packLotLinesToEdit) {
        const isAllowOnlyOneLot = product.isAllowOnlyOneLot();
        let canCreateLots = this.pickingType.use_create_lots || !this.pickingType.use_existing_lots;

        let existingLots = [];
        try {
            existingLots = await this.data.call(
                "pos.order.line",
                "get_existing_lots",
                [this.company.id, product.id],
                { context: { config_id: this.config.id } }
            );
            if (!canCreateLots && (!existingLots || existingLots.length === 0)) {
                this.dialog.add(AlertDialog, {
                    title: _t("No existing serial/lot number"),
                    body: _t(
                        "There is no serial/lot number for the selected product, and their creation is not allowed from the Point of Sale app."
                    ),
                });
                return null;
            }
        } catch (ex) {
            console.error("Collecting existing lots failed: ", ex);
            const confirmed = await ask(this.dialog, {
                title: _t("Server communication problem"),
                body: _t(
                    "The existing serial/lot numbers could not be retrieved.\nContinue without checking the validity of serial/lot numbers?"
                ),
                confirmLabel: _t("Yes"),
                cancelLabel: _t("No"),
            });
            if (!confirmed) return null;
            canCreateLots = true;
        }

        const usedLotsQty = this.models["pos.pack.operation.lot"]
            .filter(
                (lot) =>
                    lot.pos_order_line_id?.product_id?.id === product.id &&
                    lot.pos_order_line_id?.order_id?.state === "draft"
            )
            .reduce((acc, lot) => {
                if (!acc[lot.lot_name]) {
                    acc[lot.lot_name] = { total: 0, currentOrderCount: 0 };
                }
                acc[lot.lot_name].total += lot.pos_order_line_id?.qty || 0;
                if (lot.pos_order_line_id?.order_id?.id === this.selectedOrder.id) {
                    acc[lot.lot_name].currentOrderCount += lot.pos_order_line_id?.qty || 0;
                }
                return acc;
            }, {});

        existingLots = existingLots.filter(
            (lot) => lot.product_qty > (usedLotsQty[lot.name]?.total || 0)
        );

        const existingLotsName = existingLots.map((l) => l.name);

        if (!packLotLinesToEdit.length && existingLotsName.length === 1) {
            return { newPackLotLines: [{ lot_name: existingLotsName[0] }] };
        }

        const payload = await makeAwaitable(this.dialog, EditListPopup, {
            title: _t("Lot/Serial Number(s) Required"),
            name: product.display_name,
            isSingleItem: isAllowOnlyOneLot,
            array: packLotLinesToEdit,
            options: existingLotsName,
            customInput: canCreateLots,
            uniqueValues: product.tracking === "serial",
            isLotNameUsed: (itemValue) => {
                const totalQty = existingLots.find((lt) => lt.name == itemValue)?.product_qty || 0;
                const usedQty = usedLotsQty[itemValue]
                    ? usedLotsQty[itemValue].total - usedLotsQty[itemValue].currentOrderCount
                    : 0;
                return usedQty ? usedQty >= totalQty : false;
            },
        });

        if (!payload) return null;

        const enteredLotNames = payload.map((item) => item.text);
        const loyaltyRecords = await this.data.call(
            "loyalty.card",
            "search_read",
            [
                [["code", "in", enteredLotNames]],
                ["allocated_store_id", "code"],
            ]
        );

        const invalidLots = loyaltyRecords.filter((record) => {
            const allocatedId = Array.isArray(record.allocated_store_id)
                ? record.allocated_store_id[0]
                : record.allocated_store_id;
            return allocatedId !== this.config.id;
        });

        if (invalidLots.length > 0) {
    console.warn(
        "Blocked product addition due to invalid lot(s):",
        invalidLots.map((l) => l.code || l.name)
    );

    await this.dialog.add(AlertDialog, {
        title: _t("Invalid Lot/Serial Number"),
        body: _t(
            "The following lot/serial numbers are allocated to a different location: " +
            invalidLots.map((l) => l.code || l.name).join(", ")
        ),
    });
    setTimeout(() => {
        const currentOrder = this.selectedOrder;
        if (currentOrder) {
            const lastLine = currentOrder.get_last_orderline();
            if (lastLine) {
                currentOrder.removeOrderline(lastLine);
            }
        }
    }, 0);

    return { modifiedPackLotLines: {}, newPackLotLines: [] };
}

        const modifiedPackLotLines = Object.fromEntries(
            payload.filter((item) => item.id).map((item) => [item.id, item.text])
        );

        const newPackLotLines = payload
            .filter((item) => !item.id && (canCreateLots || existingLotsName.includes(item.text)))
            .map((item) => ({ lot_name: item.text }));

        return { modifiedPackLotLines, newPackLotLines };
    },
});
