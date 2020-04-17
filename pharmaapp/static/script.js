jQuery(document).ready(function($){

	let textarea = $(".bot-footer textarea");
	let sendBtn = $(".send");
	let msgContainer = $(".bot-body");

	sendBtn.on({
		click:function(e){
			e.preventDefault();
			let msg = textarea.val();
			textarea.val("");
			sendRequest(msg);
		}
	});

	textarea.on({
		keydown:function(e){
			switch(e.keyCode){
				case 13:
					e.preventDefault();
					let msg = $(this).val();
					$(this).val("")
					sendRequest(msg)
				break;
			}
		}
	});


	function scrollDown(c){
		c.animate({scrollTop:c.prop('scrollHeight')},500)
	}

	function sendRequest(msg){



		let tpl = `
			<div class="message right">
				<div class="message--icon badge badge-pill badge-info ">
					<i class="fas fa-user fa-2x"></i>
					&nbsp;
				</div>

				<div class="message--text">
					${msg}
				</div>
			</div>
		`;

		msgContainer.append(tpl);
		scrollDown(msgContainer);


		let headers = new Headers({
			"X-Robot-Id":"PharmaBot"
		});

		let data = new FormData();
		data.append("q",msg);

		fetch("/message",{
			method:"POST",
			headers:headers,
			body:data
		})
		.then(function(response){
			if(response.ok) {
			    var contentType = response.headers.get("content-type");
				if(contentType && contentType.indexOf("application/json") !== -1) {
				    return response.json().then(function(json) {
				    	console.log(json)

				    	let tpl = `
							<div class="message">

								<div class="message--icon badge badge-pill badge-info ">
									<i class="fas fa-robot --bot-icon fa-2x"></i> 
									&nbsp;
								</div>

								<div class="message--text">
									${json.response}
								</div>
							</div>
						`;

						$(".bot-body").append(tpl)
						scrollDown(msgContainer);
				    });
				} else {
				    console.log("Oops, nous n'avons pas du JSON!");
				}
			}
			else {
			    console.log('Mauvaise réponse du réseau');
			 }
		})
		.catch(function(error){
			console.log(`Il y a eu un problème avec l'opération fetch: ${error.message}`);
		})
	}
});