import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { unaccent } from "@web/core/utils/strings";

patch(PartnerList.prototype, {

    getPartners() {
        const searchWord = unaccent((this.state.query || "").trim(), false).toLowerCase();
        const partners = this.pos.models["res.partner"].getAll().filter(partner => partner.vendor === false);
        const exactMatches = partners.filter((partner) => partner.exactMatch(searchWord));

        if (exactMatches.length > 0) {
            return exactMatches;
        }
        const numberString = searchWord.replace(/[+\s()-]/g, "");
        const isSearchWordNumber = /^[0-9]+$/.test(numberString);

        const availablePartners = searchWord
            ? partners.filter((p) =>
                  unaccent(p.searchString).includes(isSearchWordNumber ? numberString : searchWord)
              )
            : partners
                  .slice(0, 1000)
                  .toSorted((a, b) =>
                      this.props.partner?.id === a.id
                          ? -1
                          : this.props.partner?.id === b.id
                          ? 1
                          : (a.name || "").localeCompare(b.name || "")
                  );

        return availablePartners;
    }
});
