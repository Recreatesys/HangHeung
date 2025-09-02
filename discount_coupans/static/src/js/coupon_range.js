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
            secondInputValue: "",
            secondSelectedOptionValue: null,
            secondHideOptions: true,
        });
        this.optionsDropdownRef2 = useRef("options-dropdown-2");

        useEffect(() => {
            if (this.optionsDropdownRef2.el) {
                this.setupOptionsDropdown(this.optionsDropdownRef2.el);
            }
        });

        const handleClickOutside = (event) => {
            const dropdownEl = this.optionsDropdownRef2.el;
            const inputEl = document.getElementById("lot_id"); // select input by id
            if (dropdownEl && inputEl) {
                if (!dropdownEl.contains(event.target) && !inputEl.contains(event.target)) {
                    this.state.secondHideOptions = true;
                }
            }
        };

        useEffect(() => {
            document.addEventListener("click", handleClickOutside);
            return () => document.removeEventListener("click", handleClickOutside);
        });
    },

    get secondDisplayedOptions() {
        const options = this.props.getOptions();
        if (!this.props.customInput) {
            return options;
        }
        return options.filter((o) => o.includes(this.state.secondInputValue));
    },

    onSecondInput(event) {
        this.state.secondInputValue = event.target.value;
        this.onResetSecondOptionsDropdown();
    },
    onSecondKeyup(event) {
        if (event.key === "Enter") {
            if (this.state.secondSelectedOptionValue) {
                this.onSecondSelectOption(this.state.secondSelectedOptionValue);
            }
        }
    },
    onSecondKeydown(event) {
        let optionSelectionRelativeMove = 0;
        if (event.key === "ArrowDown") optionSelectionRelativeMove = 1;
        else if (event.key === "ArrowUp") optionSelectionRelativeMove = -1;

        if (optionSelectionRelativeMove !== 0) {
            event.preventDefault();
            if (this.secondDisplayedOptions.length > 0) {
                const curIndex = this.state.secondSelectedOptionValue
                    ? this.secondDisplayedOptions.findIndex((o) => o === this.state.secondSelectedOptionValue)
                    : null;
                let nextIndex = curIndex !== null ? (curIndex + optionSelectionRelativeMove) % this.secondDisplayedOptions.length : 0;
                if (nextIndex < 0) nextIndex = this.secondDisplayedOptions.length - 1;

                this.state.secondSelectedOptionValue = this.secondDisplayedOptions[nextIndex];
            }
        }
    },
    onSecondBlur() {
        this.state.secondSelectedOptionValue = null;
    },
    onSecondClick() {
        this.onResetSecondOptionsDropdown();
    },
    onSecondSelectOption(option) {
        this.state.secondInputValue = option;
        this.state.secondSelectedOptionValue = null;
        this.state.secondHideOptions = true;
    },
    onResetSecondOptionsDropdown() {
        if (this.state.secondHideOptions) {
            this.state.secondHideOptions = false;
        }
        this.state.secondSelectedOptionValue = null;
    }
});

patch(EditListPopup, {
    props: {
        ...EditListPopup.props,
        product_id: { type: String, optional: true },
    },
});
patch(EditListPopup.prototype, {
    confirm() {
        const pos = this.env.services.pos;
        const order = this.env.services.pos.get_order();
        const product = this.env.services.pos.models['product.product'].get(parseInt(this.props.product_id));
        const lot_qty = parseInt($('.edit-list-inputs #lot_qty').val())
        const current_sr = $('.edit-list-inputs .list-line-input').val()
        const end_sr = $('.edit-list-inputs input[placeholder="End Serial/Lot Number"]').val()

        if (!product) {
            this.env.services.dialog.add(AlertDialog, {
                title: "Validation Error",
                body: "No product found for this lot assignment.",
            });
            return;
        }

        if (!current_sr || !end_sr) {
            this.env.services.dialog.add(AlertDialog, {
                title: "Validation Error",
                body: "Please select both Start and End serial/lot numbers.",
            });
            return;
        }

        const startIndex = this.props.options.indexOf(current_sr);
        const endIndex = this.props.options.indexOf(end_sr);

        if (startIndex === -1 || endIndex === -1) {
            this.env.services.dialog.add(AlertDialog, {
                title: "Validation Error",
                body: "Selected start or end serial/lot is not available in options.",
            });
            return;
        }

        if (startIndex > endIndex) {
            this.env.services.dialog.add(AlertDialog, {
                title: "Validation Error",
                body: `Start lot ${current_sr} must come before End lot ${end_sr}.`,
            });
            return;
        }

        const fromIndex = Math.min(startIndex, endIndex);
        const toIndex = Math.max(startIndex, endIndex);

            if (startIndex !== -1) {
                const selectedLots = this.props.options.slice(startIndex, startIndex + lot_qty);

        const selectedLots = this.props.options.slice(fromIndex, toIndex + 1);

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
