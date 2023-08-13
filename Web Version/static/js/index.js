$(document).ready(() => {
    $(".close-error-modal").click(() => {
        $(".error-modal").fadeOut()
    })
    var tasks = 0

    $(".modal-close-btn").hover(() => {
        $(".modal-close-btn").text("Close")
    }, () => {
        $(".modal-close-btn").text("")
    })

    $(".modal-close-btn").click(() => {
        $(".result-container").hide()
        $(".search-time").hide();
        $("#search").val("")
        setTimeout(() => {
            $(".main-container").fadeIn()
        }, 500)
        $(".error-modal").fadeOut()
    })

    let intervalId = null;
    let currentTime = 0;

    timer = (status = true) => {
        $(".search-time").fadeIn();

        if (status) {
            currentTime = 0;
            intervalId = setInterval(() => {
                currentTime++;
                displayTime(currentTime);
            }, 1000);
        } else {
            clearInterval(intervalId);
        }
    };

    displayTime = (time) => {
        const minutes = Math.floor(time / 60).toString().padStart(2, '0');
        const seconds = (time % 60).toString().padStart(2, '0');
        $("#timer").text(`${minutes}:${seconds}`);
    }

    search = (query) => {
        tasks++
        $.ajax({
            url: "/search",
            method: "GET",
            timeout: 600000,
            data: {search: query},
            success: function (search) {
                $(".loader").fadeIn().text("preparing")
                setTimeout(() => {
                    $(".search-loading").fadeOut()
                    timer(false)
                }, 2000)
                setTimeout(() => {
                    $(".result-container").fadeIn()
                }, 2500)

                if (search['result']) {
                    $(".error-modal div").text(search['result'])
                    setTimeout(() => {
                        $(".error-modal").fadeIn()
                    }, 500)
                    $(".main-container").fadeOut()
                } else {
                    for (let i = 0; i < Object.keys(search).length; i++) {
                        let driveName = Object.keys(search)[i]

                        let driveResult = search[driveName]

                        let resultTitle = `<div class="result-title">result for drive <span>${driveName}</span></div>`

                        $(resultTitle).appendTo($(".result-box"))

                        for (let i = 0; i < driveResult.length; i++) {
                            let resultItem = `<div class="result">${i + 1} - <a href="/open/${driveResult[i][3]}" target="_blank">${driveResult[i][0]}</a> - ration: ${driveResult[i][1]} - ${driveResult[i][2]}</div>`

                            $(resultItem).appendTo($(".result-box"))
                        }
                    }
                }
                tasks--
            }
        });

    }

    $('.search-btn').click(() => {
        var search_input = $("#search").val()
        $(".result-container").fadeOut()
        $(".result-box").empty()
        if (search_input !== '') {
            if (tasks < 1) {
                $(".search-loading").fadeIn()
                $(".loader").text("Searching")
                timer(true)
                search(search_input)
            } else {
                setTimeout(() => {
                    $(".error-modal").fadeIn()
                }, 500)
                $(".main-container").fadeOut()
            }
        } else {
            $(".error-modal div").text("Type something to search!")
            setTimeout(() => {
                $(".error-modal").fadeIn()
            }, 500)
            $(".main-container").fadeOut()
        }
    })
});