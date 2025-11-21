/** @odoo-module */

import { Component, xml } from "@odoo/owl";

export class CustomAlert extends Component {
    static template = xml`
        <div class="pos-reorder-overlay">
            <div class="pos-reorder-modal">
                <h3 class="pos-reorder-title"><t t-esc="props.title"/></h3>
                <div class="modal-body">
                    <p><t t-esc="props.message"/></p>
                </div>
                <div class="pos-reorder-actions">
                    <button type="button" class="btn-confirm" t-on-click="this.confirm">
                        OK
                    </button>
                </div>
            </div>
        </div>
    `;

    static props = {
        title: { type: String },
        message: { type: String },
        resolve: { type: Function },
        // container: { type: Object },
    };

    /**
     * When "OK" is clicked, resolve the promise to close the popup.
     */
    confirm() {
        console.log(" ok buttoon colled");
        
        this.props.resolve({ confirmed: true });
    }
}