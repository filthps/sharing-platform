const PAGE_NUMBER_VAR = "page" // Имя параметра в url
const ITEM_SHOW_PATHNAME = "ad/show/"  // Неполный путь до страницы просмотра предмета


get_url_param_value = (name) => {
    /* Получить значение параметра в url */
    let params = document.location.search.split(RegExp(/\?|\&[A-Za-z]+\=[0-9]+/));
    for (var r = 0; r < params.length; r++) {
        var joined_value = params[r].split("=");
        if (joined_value[0].slice(1, joined_value[0].length) == name) {
            return joined_value[1];
        }
    }
};
get_new_location = (old_value, new_value, is_api, param_name) => {
    /* Получить url, заменив (old_value) и/или добавив значение (new_value),
     is_api == true - Добавит format=json,
     is_api == false - Удалит format=json,

     */
    let params = document.location.search.split(RegExp(/\?|\&[A-Za-z]+\=[0-9]+/));
    var cleaned_params = [];
    for (var i = 0; i < params.length; i++) {
        if (params[i].split("=")[0] == param_name) {
            cleaned_params.push(params[i].replace(params[i].slice(params[i].indexOf("=") + 1, params[i].length - 1), new_value));
        }
        if (params[i] == "") {
            continue
        }
        if (params[i] == document.location || params[i] == document.location.pathname ||
         params[i] == document.location.origin) {
            continue
        }
        cleaned_params.push(params[i]);
    }
    if (!cleaned_params.includes(param_name)) {
        cleaned_params.push(param_name + "=" + new_value);
    }
    if (is_api) {
        cleaned_params.push("format=json")
        }
    return document.location.pathname + "?" + cleaned_params.join("&")
};
remove_param = (param_name, url) => {
    /* Полностью удалить параметр и его значение из адресной строки */
    let params = (url || document.location.search).split(RegExp(/\?|\&[A-Za-z]+\=[0-9]+/));
    var cleaned_params = [];
    if (params.length == 0) {
        return url || document.location;
    }
    for (var i = 0; i < params.length; i++) {
        if (params[i] == "") {
            continue
        }
        if (params[i] == document.location || params[i] == document.location.pathname ||
         params[i] == document.location.origin) {
            continue
        }
        if (params[i].split("=")[0] != param_name) {
            cleaned_params.push(params[i]);
        }
    }
    if (cleaned_params.length > 1) {
        return document.location.pathname + "?" + cleaned_params.join("&");
    }
    if (cleaned_params.length == 1) {
        return document.location.pathname + "?" + cleaned_params[0];
    }
    return document.location.pathname;
};
add_param = (param_and_value, url) => {
    var url = url || document.location.search;
    if (url.includes("?")) {
        return url + "&" + param_and_value;
    } else {
        return url + "?" + param_and_value;
    }
};
list_element_factory = (data_raw, is_next_page) => {
 /* Создать и вставить в документ новые элементы */
    create_li_element = (data) => {
        get_item_url = (id) => {
            return document.location.host + "/" + ITEM_SHOW_PATHNAME + "/" + id + "/";
        };
        let li_elem = document.createElement("li");
        var img = document.createElement("img");
        if (data.image) {
            img.src = data.image;
        } else {
            img.src = "/static/ad/images/no_preview.png";
            img.class = "no-image";
        }
        li_elem.setAttribute("value", data["id"]);
        let name = document.createElement("h3");
        let link = document.createElement("a");
        name.appendChild(link);
        link.innerText = data["name"];
        link.href = get_item_url(data["id"]);
        let status = document.createElement("span");
        status.innerText = get_text()["item_status"] + ":" + get_text()[data["status"]];
        li_elem.appendChild(name);
        li_elem.appendChild(img);
        li_elem.appendChild(status);
        return li_elem;
    };
    for (var i = 0; i < data_raw.length; i++) {
        var li = create_li_element(data_raw[i]);
        var ul = document.querySelector(".items_row");
        if (is_next_page) {
            ul.appendChild(li);
        } else {
            ul.insertBefore(li, ul.firstChild);
        }
    }
};
load_prev = () => {
        if (is_wait_response) {
            return
        }
        var page_counter = Math.min(...loaded_pages_numbers);
        if (page_counter <= 0) {
            page_counter = 1;
            return
        }
        var prev_page = page_counter - 1;
        if (prev_page == 0) {
            return
        }
        var is_wait_response = true;
        fetch(get_new_location(page_counter, prev_page, true, "page"), {
            headers: {
                "X-Requested_With": "XMLHTTPRequest",
                "X-CSRFToken": get_token(),
                'Content-Type': 'application/json',
            },
            method: "GET"}).then(response => {
                if (!response.ok) {
                    var is_wait_response = false;
                    throw new Error(response.status);
                }
                response.json().then((data) => {
                    if (data) {
                        list_element_factory(data, false);
                        let new_path = get_new_location(page_counter, prev_page, false, "page")
                        history.pushState(null, null, new_path);
                        loaded_pages_numbers.push(prev_page);
                        var is_wait_response = false;
                    }
                })
      });
    };
load_next = (url) => {
    if (is_wait_response) {
            return
        }
    var is_wait_response = true;
    var page_counter = Math.max(...loaded_pages_numbers);
    var next_page = page_counter + 1;
    var url = url || get_new_location(page_counter, next_page, true, "page");
    fetch(url, { headers: {
        "X-Requested_With": "XMLHTTPRequest",
        "X-CSRFToken": get_token(),
        'Content-Type': 'application/json',
        }, method: "GET",
    }).then((response) => {
        if (!response.ok) {
            var is_wait_response = false;
            throw new Error(response.status);
            }
        response.json().then((data) => {
            if (data) {
                list_element_factory(data, true);
                if (!url) {
                let new_path = get_new_location(page_counter, next_page, false, "page");
                history.pushState(null, null, new_path);
                loaded_pages_numbers.push(next_page);
                }
                var is_wait_response = false;
            }
        })
    });
};
remove_all_elements_from_list = () => {
    document.querySelector(".items_row").innerHTML = "";
};
var is_wait_response = false;
var current_page = get_current_page() || 1;
var loaded_pages_numbers = [Number(current_page)];
(function() {
    if (get_url_param_value("page") == 1) {
        var is_page_load_from_1_page = true;
    } else {
        var is_page_load_from_1_page = false;
    }
    is_scroll_min_or_max = (event) => {
        const max_scroll_pos = document.body.scrollHeight - window.innerHeight;
        if (window.scrollY == 0) {
        if (is_page_load_from_1_page) {
            return
        }
            load_prev();
        }
        if (window.scrollY == max_scroll_pos) {
            load_next();
        }
    };
    document.addEventListener("scroll", is_scroll_min_or_max);
})();
