import argparse
import torch 
import torch.nn as nn
import torchvision
import torchvision.transforms as transforms
import wandb

# Device configuration
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

# Settings / hyperparameters
# these defaults can be edited here, via command line, or in the sweeps yaml
MODEL_NAME ="cnn example"
EPOCHS = 10
NUM_CLASSES = 10
BATCH_SIZE = 32
LEARNING_RATE = 0.001
L1_SIZE = 32
L2_SIZE = 128
# note that changing this may require changing the shape of adjacent layers
CONV_KERNEL_SIZE = 5

# Convolutional neural network (two convolutional layers)
class ConvNet(nn.Module):
    def __init__(self, args, num_classes=10):
        super(ConvNet, self).__init__()
        self.layer1 = nn.Sequential(
            nn.Conv2d(1, args.l1_size, args.conv_kernel_size, stride=1, padding=2),
            nn.BatchNorm2d(args.l1_size),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2))
        self.layer2 = nn.Sequential(
            nn.Conv2d(args.l1_size, args.l2_size, args.conv_kernel_size, stride=1, padding=2),
            nn.BatchNorm2d(args.l2_size),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2))
        self.fc = nn.Linear(7*7*args.l2_size, num_classes)
        
    def forward(self, x):
        # uncomment to see the shape of a given layer:
        #print("x: ", x.size())
        out = self.layer1(x)
        out = self.layer2(out)
        out = out.reshape(out.size(0), -1)
        out = self.fc(out)
        return out

def train(args):
    # MNIST dataset
    train_dataset = torchvision.datasets.MNIST(root='../../data/',
                                           train=True, 
                                           transform=transforms.ToTensor(),
                                           download=True)

    test_dataset = torchvision.datasets.MNIST(root='../../data/',
                                          train=False, 
                                          transform=transforms.ToTensor())

    # Data loader
    train_loader = torch.utils.data.DataLoader(dataset=train_dataset,
                                           batch_size=args.batch_size, 
                                           shuffle=True)

    test_loader = torch.utils.data.DataLoader(dataset=test_dataset,
                                          batch_size=args.batch_size, 
                                          shuffle=False)

    # set up this experiment run for logging to wandb
    wandb.init(name=args.model_name, project="pytorch_intro")
    
    # save any hyperparameters/settings from this file as defaults to wandb
    # optionally allow overrides/updates from a separate yaml file specifying hyperparameter sweeps
    cfg = wandb.config
    cfg.setdefaults(args)

    model = ConvNet(args, NUM_CLASSES).to(device)
    model.cuda()
    # log gradients and parameters to wandb
    wandb.watch(model, log="all")

    # Loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)

    # Train the model
    total_step = len(train_loader)
    for epoch in range(args.epochs):
        for i, (images, labels) in enumerate(train_loader):
            images = images.to(device)
            labels = labels.to(device)
        
            # Forward pass
            outputs = model(images)
            loss = criterion(outputs, labels)
        
            # Backward and optimize
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            # log loss to wandb
            wandb.log({"loss" : loss})
            if (i+1) % 100 == 0:
                print ('Epoch [{}/{}], Step [{}/{}], Loss: {:.4f}' 
                   .format(epoch+1, args.epochs, i+1, total_step, loss.item()))


        # Test the model
        model.eval()  # eval mode (batchnorm uses moving mean/variance instead of mini-batch mean/variance)
        with torch.no_grad():
            correct = 0
            total = 0
            for images, labels in test_loader:
                images = images.to(device)
                labels = labels.to(device)
                outputs = model(images)
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
	  
            acc = 100 * correct / total
            # log acc to wandb (and epoch so you can sync up model performance across batch sizes)
            wandb.log({"epoch" : epoch, "acc" : acc})
            print('Test Accuracy of the model on the 10000 test images: {} %'.format(100 * correct / total))

    # Save the model checkpoint
    torch.save(model.state_dict(), 'model.ckpt')

if __name__ == "__main__":
  parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
    "-m",
    "--model_name",
    type=str,
    default=MODEL_NAME,
    help="Name of this model/run")
  parser.add_argument(
    "-b",
    "--batch_size",
    type=int,
    default=BATCH_SIZE,
    help="Batch size")
  parser.add_argument(
    "-e",
    "--epochs",
    type=int,
    default=EPOCHS,
    help="Number of training epochs")
  parser.add_argument(
    "--l1_size",
    type=int,
    default=L1_SIZE,
    help="size of first conv layer")
  parser.add_argument(
    "--l2_size",
    type=int,
    default=L2_SIZE,
    help="size of second conv layer")
  parser.add_argument(
    "-lr",
    "--learning_rate", 
    type=float,
    default=LEARNING_RATE,
    help="learning rate")
  parser.add_argument(
    "-k",
    "--conv_kernel_size",
    type=int,
    default=CONV_KERNEL_SIZE,
    help="kernel size for convolutional layers (changes may require adjustment to adjacent layer shapes")
  
  args = parser.parse_args()
  train(args)
