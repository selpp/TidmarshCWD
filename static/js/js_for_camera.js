

function ModifyImageFromURL(UrlForImage){

	var c = document.getElementById("main_picture");
	var ctx = c.getContext("2d");
	var img = new Image();
	
	img.onload = function() {
    	ctx.drawImage(img, 0, 0, 615, (img.height * 615) / img.width);
	}
	img.src = UrlForImage;

	var MainElem = document.getElementById("main_picture")
	MainElem.width = 615;
	MainElem.height = (img.height * 615) / img.width;

	document.getElementById('saisie_text').value = "";
}

function TakeMain(cameraCliked){
	var element =document.getElementById(cameraCliked);
	var ImageWidth = element.width;
	var ImageHeight = element.height;
	var calcul = (ImageHeight * 615)/ImageWidth;

	var img = new Image;
	var canvas = document.getElementById("main_picture");
    var ctx = canvas.getContext("2d");
    var img = document.getElementById(cameraCliked);

    img.onload = function(){
  		ctx.drawImage(img,0,0, 615, calcul); // Or at whatever offset you like
	};
	img.src = document.getElementById(cameraCliked).src;
	var MainElem = document.getElementById("main_picture")
	MainElem.width = 615;
	MainElem.height = calcul;
}

function ArrayInput(){
	var ArrayReturned = new Array();
	var sizeI = 500;
	var sizeJ = 300;
	for (var i = 0; i<sizeI; i++) {
		ArrayReturned[ArrayReturned.length] = new Array();
	}
	
	for (var i = 0; i<sizeI; i++) {
		for (var j = 0; j<sizeJ; j++) {
			ArrayReturned[i][ArrayReturned[i].length] = [0,0,255,255];
		}
	}

	return ArrayReturned;
}

function ModifyImageFromArray(IdOfImage, arr){

	var ImaWidth = document.getElementById(IdOfImage).width;
	var ArrayWidth = arr.length;
	var ArrayHeigth = arr[0].length;
	var c = document.getElementById(IdOfImage);
	var ctx = c.getContext('2d');
	var imgData = ctx.createImageData(ArrayWidth, ArrayHeigth);

	var i;
	var x=0;
	var y=0;
	for (i=0; i<imgData.data.length; i+=4) {
		if (x==ArrayWidth) {
			x=0;
			y++;
		}

    	imgData.data[i+0] = arr[x][y][0];
    	imgData.data[i+1] = arr[x][y][1];
    	imgData.data[i+2] = arr[x][y][2];
    	imgData.data[i+3] = 255;
    	x++;
	}

	var MainElem = document.getElementById("main_picture")
	MainElem.width = ArrayWidth;
	MainElem.height = ArrayHeigth;

	ctx.putImageData(imgData,0,0);
}