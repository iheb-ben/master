try:
    import master
except KeyboardInterrupt:
    master = None


if __name__ == '__main__':
    if master:
        master.main()
