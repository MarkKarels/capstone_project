const question = document.querySelector(".question");
const choices = Array.from(document.querySelectorAll(".choice-text"));
const progressText = document.querySelector("#progressText");
const scoreText = document.querySelector("#score");
const progressBarFull = document.querySelector("#progressBarFull");
const timeLeftText = document.querySelector("#timeLeft");

let currentQuestion = {};
let acceptingAnswers = true;
let score = 0;
let questionCounter = 0;
let availableQuestions = [];
let timeLeft = 20;
let timerInterval;

let questions = [];

fetch("/api/questions")
	.then((response) => response.json())
	.then((data) => {
		questions = data;
		startGame();
	})
	.catch((error) => console.error("Error fetching questions:", error));

const MAX_QUESTIONS = 5;

startGame = () => {
	questionCounter = 0;
	score = 0;
	availableQuestions = [...questions];
	getNewQuestion();
};

getNewQuestion = () => {
	if (availableQuestions.length === 0 || questionCounter > MAX_QUESTIONS) {
		localStorage.setItem("mostRecentScore", score.toFixed(2));

		return window.location.assign(endUrl);
	}

	clearInterval(timerInterval);
	timeLeft = 20;
	timeLeftText.innerText = timeLeft.toFixed(2);

	questionCounter++;
	progressText.innerText = `Question ${questionCounter} of ${MAX_QUESTIONS}`;
	progressBarFull.style.width = `${(questionCounter / MAX_QUESTIONS) * 100}%`;

	const questionIndex = Math.floor(Math.random() * availableQuestions.length);
	currentQuestion = availableQuestions[questionIndex];
	question.innerText = currentQuestion.question;

	choices.forEach((choice) => {
		const number = choice.dataset["number"];
		choice.innerText = currentQuestion["choice" + number];
	});

	availableQuestions.splice(questionIndex, 1);

	acceptingAnswers = true;
	choices.forEach((choice) => {
		choice.parentElement.classList.add("hidden");
	});

	setTimeout(() => {
		choices.forEach((choice) => {
			choice.parentElement.classList.remove("hidden");
		});
		startTimer();
	}, 5000);
};

function startTimer() {
	timeLeft = 20;
	timeLeftText.innerText = timeLeft.toFixed(2);

	timerInterval = setInterval(() => {
		timeLeft -= 0.01;
		timeLeftText.innerText = timeLeft.toFixed(2);

		if (timeLeft <= 0) {
			clearInterval(timerInterval);
			timeLeftText.innerText = "0.00";
			incrementScore(0);
			getNewQuestion();
		}
	}, 10);
}

choices.forEach((choice) => {
	choice.addEventListener("click", (e) => {
		if (!acceptingAnswers) return;

		acceptingAnswers = false;
		clearInterval(timerInterval);

		const selectedChoice = e.target;
		const selectedAnswer = selectedChoice.dataset["number"];

		let classToApply =
			selectedAnswer == currentQuestion.answer ? "correct" : "incorrect";

		if (classToApply === "correct") {
			incrementScore(timeLeft * 5);
		}

		selectedChoice.parentElement.classList.add(classToApply);

		setTimeout(() => {
			selectedChoice.parentElement.classList.remove(classToApply);
			getNewQuestion();
		}, 3000);
	});
});

incrementScore = (num) => {
	score += num;
	scoreText.innerText = score.toFixed(2);
};
