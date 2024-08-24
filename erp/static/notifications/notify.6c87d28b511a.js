var notify_badge_class;
var notify_menu_class;
var notify_api_url;
var notify_fetch_count;
var notify_unread_url;
var notify_mark_all_unread_url;
var notify_refresh_period = 15000;
var notify_mark_as_read = false;
var consecutive_misfires = 0;
var registered_functions = [];

function fill_notification_badge(data) {
    var badges = document.getElementsByClassName(notify_badge_class);
    if (badges) {
        for (var i = 0; i < badges.length; i++) {
            badges[i].innerHTML = data.unread_count;
        }
    }
}

function fill_notification_list(data) {
    var menus = document.getElementsByClassName(notify_menu_class); 
    if (menus) {
        for (var i = 0; i < menus.length; i++) {
            var menu = menus[i];           
            // Create a container for notifications with a border
            var notificationContainer = document.createElement('div');
            notificationContainer.className = 'notification-container cursor-pointer ';  
            data.unread_list.forEach(function (item) {
                // Create a notification item
                var notificationItem = document.createElement('div');
                notificationItem.className = 'notification-item py-2'; // Add py-2 for padding               
                var message = "";

                if (typeof item.actor !== 'undefined') {
                    message = item.actor;
                }
                if (typeof item.verb !== 'undefined') {
                    message = message + " " + item.verb;
                }
                if (typeof item.target !== 'undefined') {
                    message = message + " " + item.target;
                }
                
                // Set the notification message
                notificationItem.textContent = "* "+message;
                
                // Add border styles to the notification item
                notificationItem.style.borderBottom = '1px solid #ccc'; // Customize border style here
                // Append the notification item to the container
                notificationItem.addEventListener('click', function () {
                    // Redirect to the 'retours-comptoir' page
                    window.location.href =item.description; // Replace with the actual URL you want to navigate to
                });
            
                notificationContainer.appendChild(notificationItem);
            });
            
            // Append the notification container to the menu
            menu.innerHTML = ''; // Clear previous content
            menu.appendChild(notificationContainer);
        }
    }
}

function register_notifier(func) {
    registered_functions.push(func);
}

function fetch_api_data() {
    // only fetch data if a function is setup
    if (registered_functions.length > 0) {
        var r = new XMLHttpRequest();
        var params = '?max=' + notify_fetch_count;

        if (notify_mark_as_read) {
            params += '&mark_as_read=true';
        }

        r.addEventListener('readystatechange', function(event) {
            if (this.readyState === 4) {
                if (this.status === 200) {
                    consecutive_misfires = 0;
                    var data = JSON.parse(r.responseText);
                    for (var i = 0; i < registered_functions.length; i++) {
                       registered_functions[i](data);
                    }
                } else {
                    consecutive_misfires++;
                }
            }
        });
        r.open("GET", notify_api_url + params, true);
        r.send();
    }
    if (consecutive_misfires < 10) {
        setTimeout(fetch_api_data, notify_refresh_period);
    } else {
        var badges = document.getElementsByClassName(notify_badge_class);
        if (badges) {
            for (var i = 0; i < badges.length; i++) {
                badges[i].innerHTML = "!";
                badges[i].title = "Connection lost!"
            }
        }
    }
}

setTimeout(fetch_api_data, 1000);