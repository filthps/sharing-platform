/* Обрабатывать формы возбуждая редиректы. Так как броузер не работает с PUT и PATCH */
(function() {
    create_response = (event) => {
    event.stopPropagation();
    event.preventDefault();
    get_method_name = (target_item) => {
        /* Если атрибута formmethod нету, то придётся всплывать до формы и искать method */
        if (!target_item.hasOwnProperty("formmethod")) {
            return target_item.parentElement.method;
        }
        return target_item.formmethod;
    };
    get_response_path = (target_item) => {
        /* Если атрибута formaction нету, то придётся всплывать до формы и искать action */
        if (!target_item.hasOwnProperty("formaction")) {
            return target_item.parentElement.action;
        }
        return target_item.formaction;
    };
    var method = get_method_name(event.target);
    var path = get_response_path(event.target);
    fetch(path, {
    method: method,
    headers: {"X-Requested_With": "XMLHTTPRequest",
            "X-CSRFToken": get_token(),
            'Content-Type': 'application/json'}
            }).then(data => console.log(data));
         }
    add_events = () => {
    var buttons = document.querySelectorAll('input[type="submit"]');
    for (let i=0; i<buttons.length; i++) {
        //buttons[i].addEventListener("click", create_response);
    }
    };add_events();
})();
