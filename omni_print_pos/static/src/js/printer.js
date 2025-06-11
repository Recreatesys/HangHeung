/** @odoo-module **/

import { BasePrinter } from "@point_of_sale/app/printer/base_printer"
import { _t } from "@web/core/l10n/translation"

export class OmniPrinter extends BasePrinter {
    setup({ pos, proxyUrl = "http://127.0.0.1:32276" }) {
        super.setup(...arguments)

        this.pos = pos
        this.proxyUrl = proxyUrl
    }

    async sendPrintingJob(img) {
        try {
            let img_data;
            if (typeof img === 'object' && img.hasOwnProperty('data') && img.hasOwnProperty('isBase64') && img.isBase64) {
                img_data = img.data;
            } else {
                img_data = img;
            }
            const order = this.pos.get_order()
            const res = await fetch(`${this.proxyUrl}/print/img`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ image: img_data, doc_names: order.name }),
            })
            const data = await res.json()
            return {
                result: data.success,
                printerErrorCode: data.errorCode,
            }
        } catch (error) {
            console.error("OmniPrint error:", error)
            return {
                result: false,
                printerErrorCode: "NETWORK_ERROR",
            }
        }
    }

    async openCashbox() {
        try {
            const res = await fetch(`${this.proxyUrl}/cashbox/open`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
            })
            const data = await res.json()
            return {
                result: data.success,
                errorCode: data.errorCode,
            }
        } catch (error) {
            console.error("Open cashbox error:", error)
            return {
                result: false,
                errorCode: "NETWORK_ERROR",
            }
        }
    }

    getResultsError(printResult) {
        const errorCode = printResult.errorCode
        let message = _t("The printing request was sent to the Omni Print, but it wasn't able to print.") + "\n"

        if (errorCode) {
            message += "\n" + _t("The following error code was returned:") + "\n" + errorCode

            const extra_messages = {
                NETWORK_ERROR: _t("Unable to connect to the Omni Print. Please check if it's running and accessible."),
            }

            if (errorCode in extra_messages) {
                message += "\n" + extra_messages[errorCode]
            }
        } else {
            message += _t("Please check if the Omni Print is running and the printer is ready.")
        }

        return {
            successful: false,
            message: {
                title: _t("Printing failed"),
                body: message,
            },
        }
    }
}
