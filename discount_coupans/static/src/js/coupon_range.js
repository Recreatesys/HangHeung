/** @odoo-module **/

import { EditListPopup } from "@point_of_sale/app/store/select_lot_popup/select_lot_popup";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import {
    makeAwaitable,
    ask,
} from "@point_of_sale/app/store/make_awaitable_dialog";


patch(EditListPopup.prototype, {
    props: {
        ...EditListPopup.props,
        product_id: { type: String, optional: true },
    },
    confirm() {
        const pos = this.env.services.pos;
        const order = this.env.services.pos.get_order();
        const product = this.env.services.pos.models['product.product'].get(parseInt(this.props.product_id));
        const lot_qty = parseInt($('.edit-list-inputs #lot_qty').val())
        const current_sr = $('.edit-list-inputs .list-line-input').val()

        if (!product) {
            this.env.services.dialog.add(AlertDialog, {
                title: "Validation Error",
                body: "No product found for this lot assignment.",
            });
            return;
        }

        if (!lot_qty || lot_qty <= 0) {
            this.env.services.dialog.add(AlertDialog, {
                title: "Validation Error",
                body: "Lot quantity must be a positive number.",
            });
            return;
        }

        const startIndex = this.props.options.indexOf(current_sr);
        if (startIndex === -1) {
            this.env.services.dialog.add(AlertDialog, {
                title: "Validation Error",
                body: `Starting serial/lot (${current_sr}) not found in available options.`,
            });
            return;
        }

        if (startIndex + lot_qty > this.props.options.length) {
            this.env.services.dialog.add(AlertDialog, {
                title: "Validation Error",
                body: `Not enough lots available starting from ${current_sr}. 
                       You requested ${lot_qty}, but only ${this.props.options.length - startIndex} available.`,
            });
            return;
        }

        if (product && lot_qty && current_sr) {
            const startIndex = this.props.options.indexOf(current_sr);

            if (startIndex !== -1) {
                const selectedLots = this.props.options.slice(startIndex, startIndex + lot_qty);

                selectedLots.forEach(lotName => {

                    const orderline = order.models["pos.order.line"].create({
                        order_id: order,
                        product_id: product,
                        qty: 1,
                        price_unit: product.lst_price,
                    });

                    if (orderline) {
                        orderline.setPackLotLines({
                            modifiedPackLotLines: {},
                            newPackLotLines: [
                                {
                                    lot_name: lotName,
                                },
                            ],
                            setQuantity: true,
                        });
                    }
                });
            }
        }
        this.props.close();
    }
});

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
                {
                    context: {
                        config_id: this.config.id,
                    },
                }
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
                    "The existing serial/lot numbers could not be retrieved. \nContinue without checking the validity of serial/lot numbers ?"
                ),
                confirmLabel: _t("Yes"),
                cancelLabel: _t("No"),
            });
            if (!confirmed) {
                return null;
            }
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

        // Remove lot/serial names that are already used in draft orders
        existingLots = existingLots.filter(
            (lot) => lot.product_qty > (usedLotsQty[lot.name]?.total || 0)
        );

        // Check if the input lot/serial name is already used in another order
        const isLotNameUsed = (itemValue) => {
            const totalQty = existingLots.find((lt) => lt.name == itemValue)?.product_qty || 0;
            const usedQty = usedLotsQty[itemValue]
                ? usedLotsQty[itemValue].total - usedLotsQty[itemValue].currentOrderCount
                : 0;
            return usedQty ? usedQty >= totalQty : false;
        };

        const existingLotsName = existingLots.map((l) => l.name);
        if (!packLotLinesToEdit.length && existingLotsName.length === 1) {
            // If there's only one existing lot/serial number, automatically assign it to the order line
            return { newPackLotLines: [{ lot_name: existingLotsName[0] }] };
        }
        const payload = await makeAwaitable(this.dialog, EditListPopup, {
            title: _t("Lot/Serial Number(s) Required"),
            name: product.display_name,
            product_id: String(product.id),
            isSingleItem: isAllowOnlyOneLot,
            array: packLotLinesToEdit,
            options: existingLotsName,
            customInput: canCreateLots,
            uniqueValues: product.tracking === "serial",
            isLotNameUsed: isLotNameUsed,
        });
        if (payload) {
            // Segregate the old and new packlot lines
            const modifiedPackLotLines = Object.fromEntries(
                payload.filter((item) => item.id).map((item) => [item.id, item.text])
            );
            const newPackLotLines = payload
                .filter((item) => !item.id)
                .map((item) => ({ lot_name: item.text }));

            return { modifiedPackLotLines, newPackLotLines };
        } else {
            return null;
        }
    }
});