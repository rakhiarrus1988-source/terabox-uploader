import time

def progress_bar(current, total, prefix='', suffix='', decimals=1, length=50, fill='█', print_end='\r'):
    """Display a progress bar"""
    percent = ("{0:." + str(decimals) + "f}").format(100 * (current / float(total)))
    filled_length = int(length * current // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    if current == total:
        print()