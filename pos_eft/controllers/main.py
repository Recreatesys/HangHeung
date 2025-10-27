import base64
import io
import qrcode
import hashlib
from datetime import datetime, timedelta, timezone
from odoo import http
import requests
import logging
logger = logging.getLogger(__name__)
import random

class EFTPAYController(http.Controller):

    def generate_sign(self, payload, secret_key):
        payload = {k: v for k, v in payload.items() if k != "sign"}
        sorted_items = sorted(payload.items())
        ascii_string = "&".join(f"{k}={v}" for k, v in sorted_items)
        sign_string = f"{secret_key}{ascii_string}"
        return hashlib.sha256(sign_string.encode("utf-8")).hexdigest()

    @http.route('/eft/payment/start', type='json', auth='public')
    def start_payment(self, **kwargs):
        amount = kwargs.get('amount')
        method_id = kwargs.get('method_id')
        payment_method = http.request.env['pos.payment.method'].sudo().browse(int(method_id))

        if not payment_method or not payment_method.eft_secret_key or not payment_method.eft_user_confirm_key:
            return {"error": "Missing EFTPay credentials in POS Payment Method"}

        terminal = payment_method.use_payment_terminal
        secret_key = payment_method.eft_secret_key
        user_confirm_key = payment_method.eft_user_confirm_key

        if not amount:
            return {"error": "Missing amount"}

        try:
            amount_value = float(amount)
        except ValueError:
            return {"error": "Invalid amount format"}

        if amount_value > 1:
            amount_value = 1.00

        amount_str = "{:.2f}".format(amount_value)

        def generate_out_trade_no():
            return f"ORD{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}{random.randint(100, 999)}"

        order_id = generate_out_trade_no()
        china_tz = timezone(timedelta(hours=8))
        current_time = datetime.now(china_tz).strftime('%Y%m%d%H%M%S')

        terminal_mapping = {
            "alipay":   ("service.alipay.qrcode.PreOrder",     "Alipay",   "ALIPAYCN"),
            "wechat":   ("service.wechat.qrcode.PreOrder",     "WeChat",   "WECHATCN"),
            "fps":      ("service.fps.qrcode.PreOrder",        "FPS",      "FPS"),
            "payme":    ("service.payme.qrcode.PreOrder",      "PAYME",    "PAYME"),
            "unionpay": ("service.unionpay.qrcode.csb.PreOrder", "UnionPay", "UNIONPAY"),
        }

        if terminal not in terminal_mapping:
            return {"error": f"Unsupported terminal type: {terminal}"}

        service, paytype, payment_type = terminal_mapping[terminal]

        payload = {
            "service": service,
            "user_confirm_key": user_confirm_key,
            "transaction_amount": amount_str,
            "out_trade_no": order_id,
            "paytype": paytype,
            "buyertype": "others",
            "subject": "test",
            "time": current_time,
            "payment_type": payment_type,
            "tid": "ttt333",
            "notify_url": "https://www.merchant.com/notify/receive"
        }

        payload["sign"] = self.generate_sign(payload, secret_key)

        try:
            response = requests.post(
                "https://vmp.eftpay.com.cn/VMP/Servlet/JSAPIService.do",
                json=payload,
                timeout=10
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to EFTPay: {e}")
            return {"error": "Payment service temporarily unavailable. Please try again later."}

        try:
            data = response.json()
            logger.info(f"EFTPAY response: {data}")
            print("Raw EFTPay response:", data)
        except Exception as e:
            return {"error": f"Invalid JSON response: {str(e)}"}

        qr_url = data.get("qr_code")
        logger.info(f"QR URL: {qr_url}")
        if not qr_url:
            return {
                "error": data.get("message") or data.get("return_char") or "Failed to generate QR",
                "debug": data
            }

        qr_img = qrcode.make(qr_url)
        buffered = io.BytesIO()
        qr_img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        return {
            "transaction_id": data.get("trans_id"),
            "order_id": order_id,
            "qr_url": qr_url,
            "qr_code_base64": f"data:image/png;base64,{img_str}"
        }
