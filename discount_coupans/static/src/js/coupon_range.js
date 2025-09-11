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
import { EditListInput } from "@point_of_sale/app/store/select_lot_popup/edit_list_input/edit_list_input";
import { useRef, useEffect, } from "@odoo/owl";

patch(EditListInput.prototype, {
    setup() {
        super.setup();
        Object.assign(this.state, {
            quantityValue: "",
            secondInputValue: "",
            secondSelectedOptionValue: null,
            secondHideOptions: true,
        });
        this.optionsDropdownRef2 = useRef("options-dropdown-2");

        useEffect(() => {
            if (this.optionsDropdownRef2.el) this.setupOptionsDropdown(this.optionsDropdownRef2.el);
        });

        const handleClickOutside = (event) => {
            const dropdownEl = this.optionsDropdownRef2.el;
            const endInputEl = document.querySelector("input[placeholder='End Serial/Lot Number']");
            if (dropdownEl && endInputEl && !dropdownEl.contains(event.target) && !endInputEl.contains(event.target)) {
                this.state.secondHideOptions = true;
            }
        };

        useEffect(() => {
            document.addEventListener("click", handleClickOutside);
            return () => document.removeEventListener("click", handleClickOutside);
        });
    },

    get secondDisplayedOptions() {
        const options = this.props.getOptions();
        if (!this.props.customInput) return options;
        return options.filter((o) => o.includes(this.state.secondInputValue));
    },

    onQuantityInput(event) {
        this.state.quantityValue = event.target.value;
        this.updateEndSerial();
    },

    updateEndSerial() {
    const startInputEl = document.querySelector(".popup-input.list-line-input");
    const startSerial = startInputEl ? startInputEl.value : "";
    const quantity = parseInt(this.state.quantityValue, 10);

    if (!startSerial || isNaN(quantity) || quantity <= 0) {
        this.state.secondInputValue = "";
        return;
    }

    const match = startSerial.match(/(\D*)(\d+)$/);
    if (!match) {
        this.state.secondInputValue = "";
        return;
    }

    const prefix = match[1];
    const startNumberStr = match[2];
    const startNumber = parseInt(startNumberStr, 10);
    const endNumber = startNumber + quantity - 1;

    const endNumberStr = String(endNumber).padStart(startNumberStr.length, "0");

    this.state.secondInputValue = `${prefix}${endNumberStr}`;
}

});


patch(EditListPopup, {
    props: {
        ...EditListPopup.props,
        product_id: { type: String, optional: true },
        order: { type: Object, optional: true },
    },
});

patch(EditListPopup.prototype, {
    confirm() {
        const order = this.env.services.pos.get_order();
        if (!order) {
            this.env.services.dialog.add(AlertDialog, {
                title: "Error",
                body: "No active order found.",
            });
            return;
        }

        const pos = this.env.services.pos;
        const product = this.env.services.pos.models['product.product'].get(parseInt(this.props.product_id));

        if (!product) {
            this.env.services.dialog.add(AlertDialog, {
                title: "Validation Error",
                body: "No product found for this lot assignment.",
            });
            return;
        }

        const startSerial = $('.edit-list-inputs .list-line-input').val();
        const quantity = parseInt($('.edit-list-inputs input[placeholder="Quantity"]').val());

        if (!startSerial || isNaN(quantity) || quantity <= 0) {
            this.env.services.dialog.add(AlertDialog, {
                title: "Validation Error",
                body: "Quantity must be a positive number.",
            });
            return;
        }

        const match = startSerial.match(/(\D*)(\d+)$/);
        if (!match) {
            this.env.services.dialog.add(AlertDialog, {
                title: "Validation Error",
                body: "Start Serial format is invalid.",
            });
            return;
        }

        const prefix = match[1];
        const startNumberStr = match[2];
        const startNumber = parseInt(startNumberStr, 10);
        const endNumber = startNumber + quantity - 1;

        const availableLots = this.props.options || [];
        const availableNumbers = availableLots
            .map(lot => {
                const matchNum = lot.match(/(\d+)$/);
                return matchNum ? parseInt(matchNum[1], 10) : null;
            })
            .filter(n => n !== null);

        if (availableNumbers.length > 0) {
            const maxAvailable = Math.max(...availableNumbers);
            if (endNumber > maxAvailable) {
                this.env.services.dialog.add(AlertDialog, {
                    title: "Validation Error",
                    body: `You cannot assign beyond ${prefix}${String(maxAvailable).padStart(startNumberStr.length, "0")}. Please reduce quantity.`,
                });
                return;
            }
        }

        const orderline = order.models["pos.order.line"].create({
            order_id: order,
            product_id: product,
            qty: 1,
            price_unit: product.lst_price,
        });

        if (orderline) {
            const lots = [];
            for (let i = 0; i < quantity; i++) {
                const lotNumber = String(startNumber + i).padStart(startNumberStr.length, "0");
                lots.push({ lot_name: `${prefix}${lotNumber}` });
            }

            orderline.setPackLotLines({
                modifiedPackLotLines: {},
                newPackLotLines: lots,
                setQuantity: false,
            });
            orderline.set_quantity(quantity);
        }

        this.props.close();
    },
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
