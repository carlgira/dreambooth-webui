var days, hours, minutes, seconds, target_date, interval, countdown, redirect;

function startCountdown(secondsCountdown, redirectUrl){
	redirect = redirectUrl;
    target_date = new Date().getTime() + (1000 * secondsCountdown);
    countdown = document.getElementById("tiles"); // get tag element

    getCountdown();

    interval = setInterval(function () { getCountdown(); }, 1000);
}

function getCountdown(){
	var current_date = new Date().getTime();
	var seconds_left = (target_date - current_date) / 1000;

	days = pad( parseInt(seconds_left / 86400) );
	seconds_left = seconds_left % 86400;
		 
	hours = pad( parseInt(seconds_left / 3600) );
	seconds_left = seconds_left % 3600;
		  
	minutes = pad( parseInt(seconds_left / 60) );
	seconds = pad( parseInt( seconds_left % 60 ));
  
  if(seconds_left < 0){
    clearInterval(interval);
	window.location.href = redirect;
  }
	// format countdown string + set tag value
	countdown.innerHTML = "<p>" + hours + ":" + minutes + ":" + seconds + "</p>"; 
}

function pad(n) {
	return (n < 10 ? '0' : '') + n;
}

