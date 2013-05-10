$(document).ready(function() {
	$("#delete-button").click(function(e) {
		$(this).parents(".post-update").remove();
	});
});