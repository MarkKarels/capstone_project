document.addEventListener("DOMContentLoaded", function () {
	// When the page is loaded, fetch the high scores and display them.
	fetchHighScores();
});

function fetchHighScores() {
	console.log("Fetching high scores...");
	fetch("/getHighScores") // make a GET request to the Flask backend
		.then((response) => response.json()) // parse the JSON from the response
		.then((data) => {
			// Now that we have the high scores, let's display them:
			displayHighScores(data.high_scores);
		})
		.catch((error) => {
			console.error("Error fetching high scores:", error);
		});
}

function displayHighScores(highScores) {
	console.log("Displaying high scores:", highScores);
	const highScoresList = document.getElementById("highScoresList");
	highScoresList.innerHTML = ""; // Clear the current list, if necessary

	// Take only the top 5 scores
	highScores.slice(0, 5).forEach((score, index) => {
		// Create a new list item for each score
		const li = document.createElement("li");
		li.textContent = `${index + 1}. ${score.name} - ${score.score}`;
		// Append each list item to the list
		highScoresList.appendChild(li);
	});
}
