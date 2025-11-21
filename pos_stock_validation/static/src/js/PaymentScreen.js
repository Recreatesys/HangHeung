/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { App, onMounted } from "@odoo/owl";
import { CustomAlert } from "./validation_pop_up";

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        onMounted(() => this.injectCustomCSS());
    },

    injectCustomCSS() {
        if (document.getElementById("pos-custom-alert-style")) return;
        const css = `
            .pos-reorder-overlay { position: fixed; inset: 0; display:flex; align-items:center; justify-content:center; background: rgba(0,0,0,0.35); z-index: 9999; }
            .pos-reorder-modal { background: #fff; border-radius: 8px; padding: 16px; width: min(450px, 90vw); box-shadow: 0 8px 30px rgba(0,0,0,.2); }
            .pos-reorder-title { margin: 0 0 12px; font-size: 1.5rem; }
            .pos-reorder-actions { display:flex; justify-content:flex-end; gap: 8px; margin-top: 16px; }
            .btn-confirm { background-color: #017e84; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        `;
        const style = document.createElement("style");
        style.id = "pos-custom-alert-style";
        style.textContent = css;
        document.head.appendChild(style);
    },

    async addProductToOrder(product) {
        if (product.type === "consu" || product.type === "combo") {

            const order = this.pos.get_order();
            const lines = order.get_orderlines();
            const lastLine = lines.length ? lines[lines.length - 1] : null;
            const lastQty = lastLine ? lastLine.get_quantity() : 0;

            const lowStockResponse = await this.env.services.orm.call(
                "pos.session",
                "check_low_stock",
                [
                    this.pos.session.id,
                    { [product.id]: lastQty + 1 }   // quantity that user is trying to add
                ]
            );

            console.log("Low stock response:", lowStockResponse);
            const available = lowStockResponse[0]?.available ?? 0;

            if (available <= lastQty) {

                const container = document.createElement("div");
                document.body.appendChild(container);

                await new Promise(async (resolve) => {
                    let app;
                    const originalResolve = resolve;

                    const cleanup = async () => {
                        try {
                            if (app) await app.unmount;
                        } finally {
                            if (container.parentNode) {
                                container.parentNode.removeChild(container);
                            }
                        }
                    };

                    const wrappedResolve = async (payload) => {
                        await cleanup();
                        originalResolve(payload);
                    };

                    app = new App(CustomAlert, {
                        env: this.env,
                        props: {
                            title: "Product Out of Stock",
                            message: `'${product.display_name}' cannot be added.`,
                            resolve: wrappedResolve,
                            container,
                        },
                    });

                    await app.mount(container);
                });

                return;
            }
        }

        await super.addProductToOrder(...arguments);
    },
});

import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.hoverTimer = null;
        this.hoverPopup = null;
        onMounted(() => this.injectCustomCSS());
    },

    injectCustomCSS() {
        if (document.getElementById("pos-custom-alert-style")) {
            return;
        }

        const css = `
            .pos-reorder-overlay { 
                position: fixed; 
                inset: 0; 
                display:flex; 
                align-items:center; 
                justify-content:center; 
                background: rgba(0,0,0,0.0); /* Transparent background */
                z-index: 9999; 
                pointer-events: none; /* Make the backdrop ignore mouse events */
            }
            .pos-reorder-modal { 
                background: #fff; 
                border-radius: 8px; 
                padding: 16px; 
                width: min(450px, 90vw); 
                box-shadow: 0 8px 30px rgba(0,0,0,.2);
                pointer-events: auto; /* THIS IS THE FIX: Re-enable mouse events for the modal */
            }
        `;
        const style = document.createElement("style");
        style.id = "pos-custom-alert-style";
        style.textContent = css;
        document.head.appendChild(style);
    },
});