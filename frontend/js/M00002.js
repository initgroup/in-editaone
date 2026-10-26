(function () {
    const PAGE_CODE = "M00002";
    const {getContainerEl} = PageManager.createHelper(PAGE_CODE);
    window[PAGE_CODE] = {
        frame: null,
        init() {
            this.frame = getContainerEl(`#simpleEditFrame-${PAGE_CODE}`);
            const url = new URL("/simple-edit/", window.location.origin);
            url.searchParams.set("v", window.APP_CACHE_VERSION || "1");
            this.frame.src = url.href;
            this.onShow();
        },
        onShow() {
            if (this.frame) this.frame.title = window.M00002_PAGE_I18N?.labels?.title || "Find Key Rules";
            this.frame?.contentWindow?.SimpleEditing?.onShow?.();
        },
        beforeClose() {
            const state = this.frame?.contentWindow?.SimpleEditing?.getLifecycleState?.();
            if (state?.canClose === false) { CommonMessage.warning(state.message); return false; }
            return true;
        },
        destroy() {
            this.frame?.contentWindow?.SimpleEditing?.destroy?.();
            if (this.frame) this.frame.src = "about:blank";
            this.frame = null;
        }
    };
})();
