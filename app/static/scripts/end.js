const username = document.querySelector("#username");
const saveScoreBtn = document.querySelector("#saveScoreBtn");
const finalScore = document.querySelector("#finalScore");
const mostRecentScore = localStorage.getItem("mostRecentScore");

const highScoreForm = document.querySelector(".end-form-container");
highScoreForm.addEventListener("submit", saveHighScore);
const MAX_HIGH_SCORES = 5;

finalScore.innerText = "Your final score is " + mostRecentScore + " points!";

username.addEventListener("keyup", () => {
	saveScoreBtn.disabled = !username.value;
});

function saveHighScore(e) {
	e.preventDefault();

	const score = {
		score: mostRecentScore,
		name: username.value,
	};

	fetch("/saveHighScore", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify(score),
	})
		.then((response) => response.json())
		.then((data) => {
			window.location.assign("/leaderboard");
		})
		.catch((error) => {
			console.error("Error:", error);
		});
}
