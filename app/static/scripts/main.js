document.getElementById("generate-btn").addEventListener("click", function () {
	const options = document.querySelectorAll(".option");
	options.forEach((option) => {
		option.classList.remove("correct", "incorrect");
	});

	const selectedTeam = document.getElementById("team-select").value;

	fetch("/generate_question", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify({ team: selectedTeam }),
	})
		.then((response) => response.json())
		.then((data) => {
			document.getElementById("question").textContent = data.question;
			document.getElementById("option1").textContent = data.options[0];
			document.getElementById("option2").textContent = data.options[1];
			document.getElementById("option3").textContent = data.options[2];
			document.getElementById("option4").textContent = data.options[3];

			const optionClicked = function (event) {
				options.forEach((option, index) => {
					option.removeEventListener("click", optionClicked);
				});

				const selectedOption = event.target;
				const correctOptionIndex = data.options.indexOf(data.correct_option);
				const selectedOptionIndex = Array.from(options).indexOf(selectedOption);

				if (selectedOptionIndex === correctOptionIndex) {
					selectedOption.classList.add("correct");
				} else {
					selectedOption.classList.add("incorrect");
					options[correctOptionIndex].classList.add("correct");
				}
			};

			options.forEach((option) => {
				option.addEventListener("click", optionClicked);
			});
		})
		.catch((error) => {
			console.error("Error fetching question:", error);
		});
});

document.getElementById("fill-questions-btn").addEventListener("click", function () {
	this.disabled = true;

	let toast = document.createElement("div");
	toast.classList.add("toast");
	toast.textContent = "Filling question bank. Please wait...";
	document.body.appendChild(toast);

	setTimeout(function () {
		toast.classList.add("vanish");
		document.body.removeChild(toast);
	}, 3000);

	fetch("/fill_question_bank", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},

		body: JSON.stringify({
			team: document.getElementById("team-select").value,
		}),
	})
		.then((response) => {
			if (!response.ok) {
				throw new Error("Network response was not ok");
			}
			return response.json();
		})
		.then((data) => {
			console.log(data);
		})
		.catch((error) => {
			console.error("Request failed:", error);
		})
		.finally(() => {
			document.getElementById("fill-questions-btn").disabled = false;
		});
});
