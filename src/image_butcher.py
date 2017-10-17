from PIL import Image
import numpy as np
import imageio
from utils import *

def PILtoNpArray(image):
	return np.array(image.getdata(),np.uint8).reshape(image.size[1],image.size[0],3)

class ImageButcher:
	def __init__(self,size_factor,img_size,min_size):
		self.IMG_SIZE = img_size
		self.MIN_SIZE = min_size
		self.size_factor = size_factor
		
	def get_batches(self,image):
		batches = []
		i = 0
		image = PILtoNpArray(Image.fromarray(image).resize(self.IMG_SIZE,Image.HAMMING))
		windowSize = self.IMG_SIZE
		curr_factor = 1
		while(min(windowSize) > self.MIN_SIZE):
			batches.append(self.get_batch(image, windowSize))
			curr_factor *= self.size_factor
			windowSize = int(self.IMG_SIZE[0] / curr_factor) , int(self.IMG_SIZE[1] / (curr_factor))
			i += 1
		return batches

	def get_batch(self,image,windowSize):
	# slide a window across the image
		batch = []
		step_y = int(windowSize[1]/2)
		step_x = int(windowSize[0]/2)
		for y in range(0, image.shape[0] - step_y , step_y):
			raw = []
			for x in range(0, image.shape[1] - step_x,step_x):
				# yield the current window
				if(x + windowSize[0] > self.IMG_SIZE[0] or y + windowSize[1] > self.IMG_SIZE[1]):
					break
				raw.append(image[y:y + windowSize[1], x:x + windowSize[0]])
			if len(raw) > 0 :
				batch.append(raw)
		return batch

	def get_metadata(self,x,y,z):
		size_batch = self.IMG_SIZE[0] / self.size_factor**z , self.IMG_SIZE[1] / self.size_factor**z
		step_x = size_batch[0] / 2.0
		step_y = size_batch[1] / 2.0
		return	(size_batch,step_x * x,step_y * y)

if __name__ == "__main__":

	from utils import *
	from PIL import ImageDraw
	import argparse

	parser = argparse.ArgumentParser(description="This script allow you to try out the image segmentation")

	parser.add_argument("-f","--factor",default="1.5",help="size factor by which the batch is readuce at each iteration",type=float)
	parser.add_argument("-ims","--image_size",default="1920x1080",help="Format to which the image will be resized to perform all the process")
	parser.add_argument("-ms","--min_size",default="50",help="The minimum size that each edge of a batch is allow to attain",type=int)
	parser.add_argument("-im","--image",default="bird.jpg",help="image to segment")

	args = parser.parse_args()
	args.image_size = int(args.image_size.split("x")[0]) , int(args.image_size.split("x")[1])
	img = imageio.imread(args.image)
	batcher = ImageButcher(args.factor,args.image_size,args.min_size)
	batches = batcher.get_batches(img)

	for batch in batches:
		all_list = None
		for y in batch:
			xlist = y[0]
			for x in y[1:]:
				xlist = np.concatenate((xlist,x),axis=1)
			if all_list is None:
				all_list = xlist
			else:
				all_list = np.concatenate((all_list,xlist),axis=0)	

		#Image.fromarray(all_list).show()
	model = load_inception()
	pred = batch_label_matching(model,batches)
	image = Image.fromarray(img)
	image = image.resize(args.image_size)
	drw = ImageDraw.Draw(image)
	for z in range(len(pred)):
		for y in range(len(pred[z])):
			for x in range(len(pred[z][0])):
				#print("{0} for {1}".format(pred[z][y][x],batcher.get_metadata(x,y,z)))
				metadata = batcher.get_metadata(x,y,z)
				pos = int(metadata[1]) , int(metadata[2])
				pos2 = int(pos[0] + metadata[0][0]) , int(pos[1] + metadata[0][1])
				print(pos)
				print(pos2)
				if(len(pred[z][y][x]) == 1 and "Bee Eater" in pred[z][y][x]):
					drw.rectangle((pos , pos2),outline=(0,255,0))

	image.show()


