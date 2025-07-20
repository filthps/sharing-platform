(function() {
    const PAGE_NUMBER_VAR = "page" // Имя параметра в url
    var page_counter = get_current_page();

    get_new_location = (old_value, new_value) => {
        return document.location.href.replace("?page=" + old_value, "?page=" + new_value);
    };

    load_prev = (href) => {
    fetch(href, { headers: {
            "X-Requested_With": "XMLHTTPRequest",
            "X-CSRFToken": get_token(),
            'Content-Type': 'application/json',
        }, method: "POST",
  }).then((response) => {
    if (!response.ok) {
      throw new Error(response.status)
    }

    return response.json()
  })
    };

    load_next = (page_num) => {};

    is_scroll_min_or_max = (event) => {
        const max_scroll_pos = document.body.scrollHeight - window.innerHeight;
        if (window.scrollY == 0) {
            console.log("MIN");
        }
        if (window.scrollY == max_scroll_pos) {
            console.log("MAX");
        }
    };
    document.addEventListener("scroll", is_scroll_min_or_max);
})();
