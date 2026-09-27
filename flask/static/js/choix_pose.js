function gererChoixPose(select, promptId) {

    if (select.value === "add") {
        window.location.href = "/poses";
        return;
    }

    fetch(`/prompt/${promptId}/pose`, {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: "pose_id=" + select.value
    })
    .then(r => r.json())
    .then(data => {
        console.log("Pose sauvegardée", data);
    });
}
