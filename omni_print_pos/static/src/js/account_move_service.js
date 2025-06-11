import { patch } from "@web/core/utils/patch";
import { AccountMoveService } from "@account/services/account_move_service";
import { sendToPrinter, parseContentDisposition, removeExtension } from "@omni_print/network/download";
import { _t } from "@web/core/l10n/translation";

patch(AccountMoveService.prototype, {
    async downloadPdf(accountMoveId) {
        const response = await this.orm.call(
            "account.move",
            "action_invoice_download_pdf",
            [accountMoveId]
        );

        if (response.type === 'ir.actions.act_url') {
            const url = response.url;

            try {
                const pdfResponse = await fetch(url);
                if (!pdfResponse.ok) {
                    throw new Error('Failed to fetch file');
                }

                // Get filename from Content-Disposition header
                const contentDisposition = pdfResponse.headers.get('Content-Disposition');
                const filename = removeExtension(parseContentDisposition(contentDisposition)) || `Invoice(${accountMoveId})`;

                const blob = await pdfResponse.blob();
                const fileType = blob.type;

                if (fileType === 'application/pdf') {
                    const printData = {
                        file: blob,
                        filename: filename,
                        reportName: `account.account_invoices`,
                        reportTitle: _t("Invoice"),
                        docNames: filename
                    };

                    await sendToPrinter(printData);
                    this.env.services.notification.add(_t("Document sent to printer"), {
                        type: "success",
                    });
                } else if (fileType === 'application/zip') {
                    // Handle zip file
                    const link = document.createElement('a');
                    link.href = URL.createObjectURL(blob);
                    link.download = filename;
                    link.click();
                    URL.revokeObjectURL(link.href);
                    this.env.services.notification.add(_t("Multiple documents downloaded as ZIP"), {
                        type: "success",
                    });
                } else {
                    throw new Error('Unsupported file type');
                }
            } catch (error) {
                console.error('Error processing document:', error);
                this.env.services.notification.add(_t("Failed to process document"), {
                    type: "danger",
                });
            }
        } else {
            await this.action.doAction(response);
        }
    }
});
